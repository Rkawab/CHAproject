from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse
from variablecosts.models import VariableCost
from django.db.models import Sum
from .models import Budget, CreditCard, PaymentItem
from fixedcosts.models import FixedCost
from .forms import BudgetForm, CreditCardForm, PaymentItemForm
from django.db.models.functions import TruncMonth
from datetime import date
from largecosts.models import LargeCost
from core.utils import sort_cost_items_with_other_last


# ホーム画面を表示するビュー
@login_required  # ログインが成功した後でしか実行されないビュー
def home(request):
    # ローカルタイムゾーン基準の日付で集計する
    today = timezone.localdate()
    first_day = today.replace(day=1)

    # 今月の出費（購入日が今月のデータ）
    monthly_entries = VariableCost.objects.filter(
        purchase_date__gte=first_day, purchase_date__lte=today
    )

    # 今月の出費額の合計
    total_variable_cost = monthly_entries.aggregate(total=Sum("amount"))["total"] or 0

    # 費目ごとの合計（「その他」を最後に表示）
    cost_item_totals_raw = (
        monthly_entries.values("cost_item__name", "cost_item__id")
        .annotate(total=Sum("amount"))
        .order_by("cost_item__id")
    )

    # Pythonで「その他」を最後に並び替え
    cost_item_totals = sort_cost_items_with_other_last(cost_item_totals_raw)

    # 立替金額合計(全期間)
    payer_totals = (
        VariableCost.objects.filter(payer__isnull=False)
        .values("payer__name")
        .annotate(total=Sum("amount"))
        .order_by("payer__name")
    )

    # 今月の固定費データを取得（FixedCost）
    year = today.year
    month = today.month
    fixed_cost = FixedCost.objects.filter(year=year, month=month).first()

    total_fixed_cost = 0
    total_amount = total_variable_cost  # 初期値として変動費だけ
    missing_fixed_items = []
    rent_value = 0
    total_amount_without_rent = total_amount  # 固定費が無いなら=変動費合計

    # 予算データを取得
    budgets = {b.category: b.amount for b in Budget.objects.all()}
    fixed_budget = budgets.get("fixed", 0)
    variable_budget = budgets.get("variable", 0)
    total_budget = fixed_budget + variable_budget

    remaining_fixed = fixed_budget
    remaining_variable = variable_budget - total_variable_cost
    remaining_total = total_budget - total_variable_cost

    if fixed_cost:
        # 項目とラベルの対応（順序あり）
        items = {
            "rent": "家賃",
            "electricity": "電気代",
            "gas": "ガス代",
            "internet": "ネット代",
            "subscriptions": "サブスク代",
            "water": "水道代",  # 注意：adjustedの判定にも使う
        }

        # 水道代は半額で計算
        adjusted_water = fixed_cost.water if fixed_cost.water is not None else None
        if adjusted_water is None:
            # 前月から取得
            prev_month = month - 1 if month > 1 else 12
            prev_year = year if month > 1 else year - 1
            prev_fc = FixedCost.objects.filter(year=prev_year, month=prev_month).first()
            adjusted_water = (
                prev_fc.water if prev_fc and prev_fc.water is not None else 0
            )

        for attr, label in items.items():
            value = getattr(fixed_cost, attr)
            if value in (0, None):  # 0かNoneの場合
                if not (attr == "water" and adjusted_water != 0):
                    missing_fixed_items.append(label)

        total_fixed_cost = (
            (fixed_cost.rent or 0)
            + (fixed_cost.electricity or 0)
            + (fixed_cost.gas or 0)
            + (fixed_cost.internet or 0)
            + (fixed_cost.subscriptions or 0)
            + (adjusted_water // 2)  # 水道代は半額
        )
        total_amount = total_variable_cost + total_fixed_cost

        # 残金（予算 - 実支出）を計算
        remaining_fixed = fixed_budget - total_fixed_cost
        remaining_variable = variable_budget - total_variable_cost
        remaining_total = total_budget - total_amount

        # 家賃と家賃を除いた合計金額
        rent_value = fixed_cost.rent if fixed_cost.rent is not None else 0
        total_amount_without_rent = total_amount - rent_value

    return render(
        request,
        "home.html",
        {
            "total_amount": total_amount,
            "cost_item_totals": cost_item_totals,
            "payer_totals": payer_totals,
            "total_variable_cost": total_variable_cost,
            "total_fixed_cost": total_fixed_cost,
            "missing_fixed_items": missing_fixed_items,
            "fixed_budget": fixed_budget,
            "variable_budget": variable_budget,
            "total_budget": total_budget,
            "remaining_fixed": remaining_fixed,
            "remaining_variable": remaining_variable,
            "remaining_total": remaining_total,
            "year": year,
            "month": month,
            "rent_value": rent_value,
            "total_amount_without_rent": total_amount_without_rent,
        },
    )


@login_required
def edit_budget(request):
    budgets = {b.category: b for b in Budget.objects.all()}
    fixed_budget = budgets.get("fixed", Budget(category="fixed"))
    variable_budget = budgets.get("variable", Budget(category="variable"))

    if request.method == "POST":
        fixed_form = BudgetForm(request.POST, instance=fixed_budget, prefix="fixed")
        variable_form = BudgetForm(
            request.POST, instance=variable_budget, prefix="variable"
        )

        if fixed_form.is_valid() and variable_form.is_valid():
            fixed_form.save()
            variable_form.save()
            messages.success(request, "予算を更新しました。")
            return redirect("core:home")
    else:
        fixed_form = BudgetForm(instance=fixed_budget, prefix="fixed")
        variable_form = BudgetForm(instance=variable_budget, prefix="variable")

    return render(
        request,
        "edit_budget.html",
        {
            "fixed_form": fixed_form,
            "variable_form": variable_form,
        },
    )


@login_required
def summary(request):
    # Build last 12 months range (inclusive of current month)
    today = timezone.localdate()
    base_year = today.year
    base_month = today.month

    def y_m_offset(year: int, month: int, offset: int):
        idx = (year * 12 + (month - 1)) + offset
        y = idx // 12
        m = idx % 12 + 1
        return y, m

    # List of labels like 'YYYY-MM' oldest -> newest
    months = []
    for i in range(-11, 1):
        y, m = y_m_offset(base_year, base_month, i)
        months.append((y, m))

    labels = [f"{y:04d}-{m:02d}" for y, m in months]

    # Variable costs monthly sums using TruncMonth
    start_year, start_month = months[0]
    end_year, end_month = months[-1]

    start_date = date(start_year, start_month, 1)
    # Next month after end
    ny, nm = y_m_offset(end_year, end_month, 1)
    next_month_after_end = date(ny, nm, 1)

    vc_qs = (
        VariableCost.objects.filter(
            purchase_date__gte=start_date,
            purchase_date__lt=next_month_after_end,
        )
        .annotate(mon=TruncMonth("purchase_date"))
        .values("mon")
        .annotate(total=Sum("amount"))
    )

    vc_map = {
        f"{rec['mon'].year:04d}-{rec['mon'].month:02d}": rec["total"] for rec in vc_qs
    }
    variable_series = [int(vc_map.get(lab, 0) or 0) for lab in labels]

    # Large costs monthly sums
    lc_qs = (
        LargeCost.objects.filter(
            purchase_date__gte=start_date,
            purchase_date__lt=next_month_after_end,
        )
        .annotate(mon=TruncMonth("purchase_date"))
        .values("mon")
        .annotate(total=Sum("amount"))
    )

    lc_map = {
        f"{rec['mon'].year:04d}-{rec['mon'].month:02d}": rec["total"] for rec in lc_qs
    }
    large_series = [int(lc_map.get(lab, 0) or 0) for lab in labels]

    # Fixed costs monthly sums using model method get_total_cost per row
    # Fetch all fixed cost rows in the year span and aggregate in Python
    min_year = months[0][0]
    max_year = months[-1][0]
    fixed_rows = FixedCost.objects.filter(year__gte=min_year, year__lte=max_year)
    fc_map = {}
    rent_map = {}
    for fc in fixed_rows:
        key = f"{fc.year:04d}-{fc.month:02d}"
        if key in labels:
            fc_map[key] = fc_map.get(key, 0) + int(fc.get_total_cost() or 0)
            rent_map[key] = int(fc.rent or 0)

    fixed_series = [int(fc_map.get(lab, 0) or 0) for lab in labels]
    rent_series = [int(rent_map.get(lab, 0) or 0) for lab in labels]

    # 家賃以外 = 変動費 + 固定費 - 家賃（念のためマイナスは0に丸め）
    total_without_rent_series = [
        max(0, int(v) + int(f) - int(r))
        for v, f, r in zip(variable_series, fixed_series, rent_series)
    ]

    # 家賃情報を取得
    rent_value = 0
    fc = FixedCost.objects.filter(year=base_year, month=base_month).first()
    if fc and fc.rent is not None:
        rent_value = int(fc.rent)

    # 今月の合計（seriesの末尾が今月）
    current_variable = int(variable_series[-1] or 0)
    current_fixed = int(fixed_series[-1] or 0)

    non_rent_value = current_variable + current_fixed - rent_value
    if non_rent_value < 0:
        non_rent_value = 0

    return render(
        request,
        "summary.html",
        {
            "labels": labels,
            "variable_series": variable_series,
            "fixed_series": fixed_series,
            "large_series": large_series,
            "current_year": base_year,
            "rent_series": rent_series,
            "total_without_rent_series": total_without_rent_series,
        },
    )


# 費用とクレジットの設定
@login_required
def payment_settings(request):
    cards = CreditCard.objects.select_related("owner").all()
    items = PaymentItem.objects.select_related("card", "card__owner").all()
    return render(
        request,
        "payment_settings.html",
        {
            "cards": cards,
            "items": items,
        },
    )


# --- CreditCard CRUD ---
@login_required
def creditcard_create(request):
    form = CreditCardForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "クレカを追加しました。")
        return redirect("core:payment_settings")
    return render(request, "payment_form.html", {"title": "クレカ追加", "form": form})


@login_required
def creditcard_edit(request, pk):
    obj = get_object_or_404(CreditCard, pk=pk)
    form = CreditCardForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "クレカを更新しました。")
        return redirect("core:payment_settings")
    return render(request, "payment_form.html", {"title": "クレカ編集", "form": form})


@login_required
def creditcard_delete(request, pk):
    obj = get_object_or_404(CreditCard, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "クレカを削除しました。")
        return redirect("core:payment_settings")
    return render(
        request,
        "payment_delete_confirm.html",
        {
            "title": "クレカ削除",
            "object": obj,
            "back_url": reverse("core:payment_settings"),
        },
    )


# --- PaymentItem CRUD ---
@login_required
def paymentitem_create(request):
    form = PaymentItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "支払い項目を追加しました。")
        return redirect("core:payment_settings")
    return render(
        request, "payment_form.html", {"title": "支払い項目追加", "form": form}
    )


@login_required
def paymentitem_edit(request, pk):
    obj = get_object_or_404(PaymentItem, pk=pk)
    form = PaymentItemForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "支払い項目を更新しました。")
        return redirect("core:payment_settings")
    return render(
        request, "payment_form.html", {"title": "支払い項目編集", "form": form}
    )


@login_required
def paymentitem_delete(request, pk):
    obj = get_object_or_404(PaymentItem, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "支払い項目を削除しました。")
        return redirect("core:payment_settings")
    return render(
        request,
        "payment_delete_confirm.html",
        {
            "title": "支払い項目削除",
            "object": obj,
            "back_url": reverse("core:payment_settings"),
        },
    )
