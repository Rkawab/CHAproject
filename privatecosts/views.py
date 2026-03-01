from datetime import timedelta
from calendar import monthrange
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Min, Max
from core.models import Payer
from core.utils import sort_cost_items_with_other_last, build_available_months
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
    shared_cost = (fixed_cost.shared_cost or 0) if fixed_cost else 0
    subscriptions = (fixed_cost.subscriptions or 0) if fixed_cost else 0
    balance = salary - deduction - shared_cost - subscriptions - variable_total

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
