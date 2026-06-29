import datetime
import json
from datetime import timedelta
from calendar import monthrange
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum, Min, Max
from django.db.models.functions import TruncMonth
from django.views.decorators.http import require_POST
from core.models import Payer, CostItem
from core.utils import sort_cost_items_with_other_last, build_available_months
from core.receipt_reader import ReceiptReadError, extract_receipt_info
from fixedcosts.models import FixedCost
from variablecosts.models import VariableCost
from largecosts.models import LargeCost
from .models import (
    PrivateVariableCost,
    PrivateFixedCost,
    PrivateAnnualInfo,
    PrivateSubscription,
)
from .forms import (
    PrivateVariableCostForm,
    PrivateFixedCostForm,
    PrivateAnnualInfoForm,
    PrivateSubscriptionForm,
)


def _shift_year_month(year, month, offset):
    idx = year * 12 + (month - 1) + offset
    return idx // 12, idx % 12 + 1


def _month_key(year, month):
    return f"{year:04d}-{month:02d}"


def _household_shared_cost_map(months, start_date, end_date):
    month_keys = {_month_key(y, m) for y, m in months}
    min_year = months[0][0]
    max_year = months[-1][0]

    fixed_map = {}
    for fixed_cost in FixedCost.objects.filter(year__gte=min_year, year__lte=max_year):
        key = _month_key(fixed_cost.year, fixed_cost.month)
        if key in month_keys:
            fixed_map[key] = fixed_map.get(key, 0) + int(
                fixed_cost.get_total_cost() or 0
            )

    variable_qs = (
        VariableCost.objects.filter(
            purchase_date__gte=start_date,
            purchase_date__lt=end_date,
        )
        .annotate(mon=TruncMonth("purchase_date"))
        .values("mon")
        .annotate(total=Sum("amount"))
    )
    variable_map = {
        _month_key(rec["mon"].year, rec["mon"].month): int(rec["total"] or 0)
        for rec in variable_qs
    }

    return {
        key: (fixed_map.get(key, 0) + variable_map.get(key, 0)) // 2
        for key in month_keys
    }


def _large_shared_cost_map(months, start_date, end_date):
    month_keys = {_month_key(y, m) for y, m in months}
    large_qs = (
        LargeCost.objects.filter(
            purchase_date__gte=start_date,
            purchase_date__lt=end_date,
        )
        .annotate(mon=TruncMonth("purchase_date"))
        .values("mon")
        .annotate(total=Sum("amount"))
    )
    large_map = {
        _month_key(rec["mon"].year, rec["mon"].month): int(rec["total"] or 0)
        for rec in large_qs
    }
    return {key: large_map.get(key, 0) // 2 for key in month_keys}


def _safe_month(value, fallback):
    try:
        month = int(value)
    except (TypeError, ValueError):
        return fallback
    if 1 <= month <= 12:
        return month
    return fallback


def _private_subscription_map(user, labels):
    """ラベル一覧に対する使用者別サブスク合計を返す"""
    result = {}
    for label in labels:
        year, month = [int(part) for part in label.split("-")]
        result[label] = PrivateSubscription.total_for_month(user, year, month)
    return result


@login_required
def privatecosts_index(request):
    """個人用インデックスページ（Payerボタン一覧）"""
    payers = Payer.objects.all()
    return render(request, "privatecosts/index.html", {"payers": payers})


@login_required
def privatecosts_detail(request, payer_name, year=None, month=None):
    """特定Payerの個人家計簿（月ナビ + 収支カード + 変動費一覧）"""
    payer = get_object_or_404(Payer, name=payer_name)
    today = timezone.localdate()

    if year is None or month is None:
        year = today.year
        month = today.month

    # 表示対象月の開始・終了日
    start_date = today.replace(year=year, month=month, day=1)
    _, last_day = monthrange(year, month)
    end_date = start_date.replace(day=last_day)

    # 当月の変動費を取得
    variable_entries = PrivateVariableCost.objects.filter(
        user=payer,
        purchase_date__range=(start_date, end_date),
    ).order_by("purchase_date")

    variable_total = variable_entries.aggregate(total=Sum("amount"))["total"] or 0

    # 費目ごとの合計（「その他」を末尾にソート）
    cost_item_totals_raw = (
        variable_entries.values("cost_item__name", "cost_item__id")
        .annotate(total=Sum("amount"))
        .order_by("cost_item__id")
    )
    cost_item_totals = sort_cost_items_with_other_last(cost_item_totals_raw)

    # 当月の個人固定費を取得
    try:
        fixed_cost = PrivateFixedCost.objects.get(user=payer, year=year, month=month)
    except PrivateFixedCost.DoesNotExist:
        fixed_cost = None

    # 収支計算: 給与収入 - 差引控除額 - (折半費 + サブスク + 変動費合計)
    salary = (fixed_cost.salary or 0) if fixed_cost else 0
    deduction = (fixed_cost.deduction or 0) if fixed_cost else 0
    subscriptions = PrivateSubscription.total_for_month(payer, year, month)
    savings = (fixed_cost.savings or 0) if fixed_cost else 0

    # 夫婦折半費用：当月の家計合計（固定費＋変動費）の1/2を自動計算
    try:
        household_fixed = FixedCost.objects.get(year=year, month=month)
        household_fixed_total = int(household_fixed.get_total_cost())
    except FixedCost.DoesNotExist:
        household_fixed_total = 0
    household_variable_total = (
        VariableCost.objects.filter(
            purchase_date__range=(start_date, end_date)
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    shared_cost = (household_fixed_total + household_variable_total) // 2
    large_shared_cost = (
        LargeCost.objects.filter(
            purchase_date__range=(start_date, end_date)
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    ) // 2

    balance = (
        salary
        - deduction
        - shared_cost
        - large_shared_cost
        - subscriptions
        - savings
        - variable_total
    )

    # summaryページ風の直近12ヶ月グラフ用データ（表示月を終点にする）
    chart_months = [_shift_year_month(year, month, i) for i in range(-11, 1)]
    chart_labels = [_month_key(y, m) for y, m in chart_months]
    chart_start_date = datetime.date(chart_months[0][0], chart_months[0][1], 1)
    chart_end_year, chart_end_month = _shift_year_month(
        chart_months[-1][0], chart_months[-1][1], 1
    )
    chart_end_date = datetime.date(chart_end_year, chart_end_month, 1)

    chart_variable_qs = (
        PrivateVariableCost.objects.filter(
            user=payer,
            purchase_date__gte=chart_start_date,
            purchase_date__lt=chart_end_date,
        )
        .annotate(mon=TruncMonth("purchase_date"))
        .values("mon")
        .annotate(total=Sum("amount"))
    )
    chart_variable_map = {
        _month_key(rec["mon"].year, rec["mon"].month): int(rec["total"] or 0)
        for rec in chart_variable_qs
    }

    chart_deduction_map = {}
    chart_savings_map = {}
    chart_min_year = chart_months[0][0]
    chart_max_year = chart_months[-1][0]
    for row in PrivateFixedCost.objects.filter(
        user=payer, year__gte=chart_min_year, year__lte=chart_max_year
    ):
        key = _month_key(row.year, row.month)
        if key in chart_labels:
            chart_deduction_map[key] = chart_deduction_map.get(key, 0) + int(
                row.deduction or 0
            )
            chart_savings_map[key] = chart_savings_map.get(key, 0) + int(
                row.savings or 0
            )

    chart_shared_map = _household_shared_cost_map(
        chart_months, chart_start_date, chart_end_date
    )
    chart_large_shared_map = _large_shared_cost_map(
        chart_months, chart_start_date, chart_end_date
    )
    deduction_series = [chart_deduction_map.get(label, 0) for label in chart_labels]
    shared_series = [chart_shared_map.get(label, 0) for label in chart_labels]
    large_shared_series = [
        chart_large_shared_map.get(label, 0) for label in chart_labels
    ]
    chart_subscription_map = _private_subscription_map(payer, chart_labels)
    subscription_series = [
        chart_subscription_map.get(label, 0) for label in chart_labels
    ]
    savings_series = [chart_savings_map.get(label, 0) for label in chart_labels]
    private_variable_series = [
        chart_variable_map.get(label, 0) for label in chart_labels
    ]

    # 表示年の年間情報・年間収支
    annual_info = PrivateAnnualInfo.objects.filter(user=payer, year=year).first()
    annual_summer_bonus = (annual_info.summer_bonus or 0) if annual_info else 0
    annual_winter_bonus = (annual_info.winter_bonus or 0) if annual_info else 0
    annual_bonus_total = annual_summer_bonus + annual_winter_bonus
    annual_fixed_rows = PrivateFixedCost.objects.filter(user=payer, year=year)
    annual_salary = sum(int(row.salary or 0) for row in annual_fixed_rows)
    annual_deduction = sum(int(row.deduction or 0) for row in annual_fixed_rows)
    annual_savings = sum(int(row.savings or 0) for row in annual_fixed_rows)
    annual_subscriptions = sum(
        PrivateSubscription.total_for_month(payer, year, month_value)
        for month_value in range(1, 13)
    )
    annual_variable_total = (
        PrivateVariableCost.objects.filter(
            user=payer,
            purchase_date__gte=datetime.date(year, 1, 1),
            purchase_date__lt=datetime.date(year + 1, 1, 1),
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    annual_months = [(year, m) for m in range(1, 13)]
    annual_shared_cost = sum(
        _household_shared_cost_map(
            annual_months,
            datetime.date(year, 1, 1),
            datetime.date(year + 1, 1, 1),
        ).values()
    )
    annual_large_shared_cost = sum(
        _large_shared_cost_map(
            annual_months,
            datetime.date(year, 1, 1),
            datetime.date(year + 1, 1, 1),
        ).values()
    )
    annual_expense_total = (
        annual_deduction
        + annual_shared_cost
        + annual_large_shared_cost
        + annual_subscriptions
        + annual_savings
        + annual_variable_total
    )
    annual_balance = annual_salary + annual_bonus_total - annual_expense_total

    # ナビゲーション用の前月・次月
    prev_month_date = (start_date - timedelta(days=1)).replace(day=1)
    next_month_date = (end_date + timedelta(days=1)).replace(day=1)
    # 翌月が未来なら None にする
    next_month_obj = None if next_month_date > today.replace(day=1) else next_month_date

    # 月選択プルダウン用の候補生成
    agg = PrivateVariableCost.objects.filter(user=payer).aggregate(
        min_date=Min("purchase_date"), max_date=Max("purchase_date")
    )
    min_date = agg["min_date"] or start_date
    max_date = agg["max_date"] or start_date
    if max_date > today:
        max_date = today
    available_months = build_available_months(min_date, max_date)
    if not available_months:
        available_months = [{"year": year, "month": month}]

    return render(
        request,
        "privatecosts/detail.html",
        {
            "payer": payer,
            "year": year,
            "month": month,
            "variable_entries": variable_entries,
            "variable_total": variable_total,
            "cost_item_totals": cost_item_totals,
            "fixed_cost": fixed_cost,
            "salary": salary,
            "deduction": deduction,
            "shared_cost": shared_cost,
            "large_shared_cost": large_shared_cost,
            "subscriptions": subscriptions,
            "savings": savings,
            "balance": balance,
            "annual_info": annual_info,
            "annual_summer_bonus": annual_summer_bonus,
            "annual_winter_bonus": annual_winter_bonus,
            "annual_bonus_total": annual_bonus_total,
            "annual_salary": annual_salary,
            "annual_deduction": annual_deduction,
            "annual_shared_cost": annual_shared_cost,
            "annual_large_shared_cost": annual_large_shared_cost,
            "annual_subscriptions": annual_subscriptions,
            "annual_savings": annual_savings,
            "annual_variable_total": annual_variable_total,
            "annual_expense_total": annual_expense_total,
            "annual_balance": annual_balance,
            "monthly_expense_labels": json.dumps(chart_labels),
            "monthly_deduction_series": json.dumps(deduction_series),
            "monthly_shared_series": json.dumps(shared_series),
            "monthly_large_shared_series": json.dumps(large_shared_series),
            "monthly_subscription_series": json.dumps(subscription_series),
            "monthly_savings_series": json.dumps(savings_series),
            "monthly_variable_series": json.dumps(private_variable_series),
            "monthly_expense_chart_year": year,
            "prev_month": prev_month_date,
            "next_month": next_month_obj,
            "available_months": available_months,
        },
    )


@login_required
def private_variable_new(request, payer_name):
    """個人変動費の新規追加"""
    payer = get_object_or_404(Payer, name=payer_name)
    if request.method == "POST":
        form = PrivateVariableCostForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = payer
            obj.save()
            messages.success(request, "変動費を追加しました。")
            return redirect("privatecosts:detail", payer_name=payer_name)
    else:
        form = PrivateVariableCostForm()
    return render(
        request,
        "privatecosts/variable_form.html",
        {"form": form, "payer": payer},
    )


@login_required
def private_variable_edit(request, payer_name, pk):
    """個人変動費の編集"""
    payer = get_object_or_404(Payer, name=payer_name)
    entry = get_object_or_404(PrivateVariableCost, pk=pk, user=payer)
    if request.method == "POST":
        form = PrivateVariableCostForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, "変動費を更新しました。")
            return redirect("privatecosts:detail", payer_name=payer_name)
    else:
        form = PrivateVariableCostForm(instance=entry)
    return render(
        request,
        "privatecosts/variable_form.html",
        {"form": form, "payer": payer},
    )


@login_required
def private_variable_delete(request, payer_name, pk):
    """個人変動費の削除確認"""
    payer = get_object_or_404(Payer, name=payer_name)
    entry = get_object_or_404(PrivateVariableCost, pk=pk, user=payer)
    if request.method == "POST":
        entry.delete()
        messages.success(request, "変動費を削除しました。")
        return redirect("privatecosts:detail", payer_name=payer_name)
    return render(
        request,
        "privatecosts/variable_delete.html",
        {"entry": entry, "payer": payer},
    )


@login_required
def private_fixed_edit(request, payer_name, year=None, month=None):
    """個人固定費の追加・編集"""
    payer = get_object_or_404(Payer, name=payer_name)
    today = timezone.localdate()

    if year is None or month is None:
        year = today.year
        month = today.month

    # 既存データを取得、なければ未保存インスタンスを用意
    try:
        fixed_cost = PrivateFixedCost.objects.get(user=payer, year=year, month=month)
    except PrivateFixedCost.DoesNotExist:
        fixed_cost = PrivateFixedCost(user=payer, year=year, month=month)

    if request.method == "POST":
        form = PrivateFixedCostForm(request.POST, instance=fixed_cost, payer=payer)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = payer
            obj.save()
            messages.success(request, f"{year}年{month}月の個人固定費を保存しました。")
            return redirect(
                "privatecosts:detail_by_month",
                payer_name=payer_name,
                year=year,
                month=month,
            )
    else:
        form = PrivateFixedCostForm(instance=fixed_cost, payer=payer)

    return render(
        request,
        "privatecosts/fixed_form.html",
        {
            "form": form,
            "payer": payer,
            "year": year,
            "month": month,
            "is_new": not fixed_cost.pk,
        },
    )


@login_required
def private_annual_edit(request, payer_name, year):
    """個人年間情報の追加・編集"""
    payer = get_object_or_404(Payer, name=payer_name)
    today = timezone.localdate()
    return_month = _safe_month(
        request.POST.get("return_month") or request.GET.get("month"),
        today.month,
    )

    try:
        annual_info = PrivateAnnualInfo.objects.get(user=payer, year=year)
    except PrivateAnnualInfo.DoesNotExist:
        annual_info = PrivateAnnualInfo(user=payer, year=year)

    if request.method == "POST":
        form = PrivateAnnualInfoForm(request.POST, instance=annual_info, payer=payer)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = payer
            obj.save()
            messages.success(request, f"{obj.year}年の年間情報を保存しました。")
            return redirect(
                "privatecosts:detail_by_month",
                payer_name=payer_name,
                year=obj.year,
                month=return_month,
            )
    else:
        form = PrivateAnnualInfoForm(instance=annual_info, payer=payer)

    return render(
        request,
        "privatecosts/annual_form.html",
        {
            "form": form,
            "payer": payer,
            "year": year,
            "return_month": return_month,
            "is_new": not annual_info.pk,
        },
    )


@login_required
def subscription_list(request, payer_name):
    """個人用サブスク一覧"""
    payer = get_object_or_404(Payer, name=payer_name)
    subscriptions = PrivateSubscription.objects.filter(user=payer)
    return render(
        request,
        "privatecosts/subscription_list.html",
        {"payer": payer, "subscriptions": subscriptions},
    )


@login_required
def subscription_create(request, payer_name):
    """個人用サブスク新規追加"""
    payer = get_object_or_404(Payer, name=payer_name)
    form = PrivateSubscriptionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        subscription = form.save(commit=False)
        subscription.user = payer
        subscription.save()
        messages.success(request, "サブスクを追加しました。")
        return redirect("privatecosts:subscription_list", payer_name=payer_name)
    return render(
        request,
        "privatecosts/subscription_form.html",
        {"form": form, "payer": payer, "is_new": True},
    )


@login_required
def subscription_edit(request, payer_name, pk):
    """個人用サブスク編集"""
    payer = get_object_or_404(Payer, name=payer_name)
    subscription = get_object_or_404(PrivateSubscription, pk=pk, user=payer)
    form = PrivateSubscriptionForm(request.POST or None, instance=subscription)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "サブスクを更新しました。")
        return redirect("privatecosts:subscription_list", payer_name=payer_name)
    return render(
        request,
        "privatecosts/subscription_form.html",
        {
            "form": form,
            "payer": payer,
            "is_new": False,
            "subscription": subscription,
        },
    )


@login_required
def subscription_delete(request, payer_name, pk):
    """個人用サブスク削除"""
    payer = get_object_or_404(Payer, name=payer_name)
    subscription = get_object_or_404(PrivateSubscription, pk=pk, user=payer)
    if request.method == "POST":
        subscription.delete()
        messages.success(request, f"「{subscription.name}」を削除しました。")
        return redirect("privatecosts:subscription_list", payer_name=payer_name)
    return render(
        request,
        "privatecosts/subscription_delete.html",
        {"subscription": subscription, "payer": payer},
    )


@login_required
@require_POST
def scan_receipt(request, payer_name):
    """
    レシート画像を受け取り、金額・購入日・費目候補・名称を JSON で返す API。
    variablecosts の scan_receipt と同じ実装。
    """
    image_file = request.FILES.get("receipt_image")
    if not image_file:
        return JsonResponse({"error": "レシート画像が選択されていません。"}, status=400)

    try:
        info = extract_receipt_info(image_file)
    except ReceiptReadError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception:
        return JsonResponse(
            {"error": "レシートの読み取り中にエラーが発生しました。"},
            status=500,
        )

    amount = info["amount"]
    purchase_date = info["purchase_date"]
    raw_category = info["raw_category"]
    description = info["description"]

    cost_item = CostItem.objects.filter(name=raw_category).first()
    if cost_item is None:
        cost_item = CostItem.objects.filter(name="その他").first()

    response_data = {
        "amount": amount,
        "purchase_date": purchase_date,
        "description": description,
    }
    if cost_item is not None:
        response_data["cost_item_id"] = cost_item.id
        response_data["cost_item_name"] = cost_item.name

    return JsonResponse(response_data)


@login_required
def eating_out_bulk(request, payer_name, year, month):
    """外食費用の1か月分一括入力"""
    payer = get_object_or_404(Payer, name=payer_name)
    _, last_day = monthrange(year, month)

    # 「外食費用」費目を取得（なければ「その他」）
    eating_out_item = CostItem.objects.filter(name="外食費用").first()
    if eating_out_item is None:
        eating_out_item = CostItem.objects.filter(name="その他").first()

    if request.method == "POST":
        for day in range(1, last_day + 1):
            date = datetime.date(year, month, day)
            key_date = date.strftime("%Y%m%d")
            amount_str = request.POST.get(f"amount_{key_date}", "").strip()
            description = request.POST.get(f"description_{key_date}", "").strip()

            # 空または0はスキップ
            try:
                amount = int(amount_str)
            except ValueError:
                continue
            if amount <= 0:
                continue

            # 名称が未入力なら「外食」を設定
            if not description:
                description = "外食"

            # その日の既存外食費用レコードを全削除して新規作成
            PrivateVariableCost.objects.filter(
                user=payer,
                purchase_date=date,
                cost_item=eating_out_item,
            ).delete()
            PrivateVariableCost.objects.create(
                user=payer,
                purchase_date=date,
                amount=amount,
                cost_item=eating_out_item,
                description=description,
            )

        messages.success(request, f"{year}年{month}月の外食費用を一括登録しました。")
        return redirect(
            "privatecosts:detail_by_month",
            payer_name=payer_name,
            year=year,
            month=month,
        )

    # GET: 各日付の既存外食費用を取得
    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year, month, last_day)

    existing = (
        PrivateVariableCost.objects.filter(
            user=payer,
            purchase_date__range=(start_date, end_date),
            cost_item=eating_out_item,
        )
        .values("purchase_date")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("purchase_date")
    )
    existing_map = {e["purchase_date"]: e for e in existing}

    # 既存レコードの名称（1件のみの場合）
    existing_desc_map = {}
    for ev in PrivateVariableCost.objects.filter(
        user=payer,
        purchase_date__range=(start_date, end_date),
        cost_item=eating_out_item,
    ).order_by("purchase_date", "id"):
        d = ev.purchase_date
        if d not in existing_desc_map:
            existing_desc_map[d] = {"count": 0, "description": ev.description}
        existing_desc_map[d]["count"] += 1
        if existing_desc_map[d]["count"] > 1:
            existing_desc_map[d]["description"] = "－"

    # 日付ごとのデータ構築
    day_entries = []
    for day in range(1, last_day + 1):
        date = datetime.date(year, month, day)
        ex = existing_map.get(date)
        desc_info = existing_desc_map.get(date)
        day_entries.append({
            "date": date,
            "key_date": date.strftime("%Y%m%d"),
            "amount": ex["total"] if ex else "",
            "description": desc_info["description"] if desc_info else "",
        })

    return render(
        request,
        "privatecosts/eating_out_bulk.html",
        {
            "payer": payer,
            "year": year,
            "month": month,
            "day_entries": day_entries,
        },
    )


@login_required
def private_fixed_delete(request, payer_name, year, month):
    """個人固定費の削除確認"""
    payer = get_object_or_404(Payer, name=payer_name)
    fixed_cost = get_object_or_404(PrivateFixedCost, user=payer, year=year, month=month)
    if request.method == "POST":
        fixed_cost.delete()
        messages.success(
            request, f"{year}年{month}月の個人固定費データを削除しました。"
        )
        return redirect("privatecosts:detail", payer_name=payer_name)
    return render(
        request,
        "privatecosts/fixed_delete.html",
        {"fixed_cost": fixed_cost, "payer": payer},
    )
