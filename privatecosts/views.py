import datetime
from datetime import timedelta
from calendar import monthrange
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum, Min, Max
from django.views.decorators.http import require_POST
from core.models import Payer, CostItem
from core.utils import sort_cost_items_with_other_last, build_available_months
from core.receipt_reader import ReceiptReadError, extract_receipt_info
from fixedcosts.models import FixedCost
from variablecosts.models import VariableCost
from .models import PrivateVariableCost, PrivateFixedCost
from .forms import PrivateVariableCostForm, PrivateFixedCostForm


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
    subscriptions = (fixed_cost.subscriptions or 0) if fixed_cost else 0
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

    balance = salary - deduction - shared_cost - subscriptions - savings - variable_total

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
            "subscriptions": subscriptions,
            "savings": savings,
            "balance": balance,
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
