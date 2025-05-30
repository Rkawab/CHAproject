from datetime import date, timedelta
from calendar import monthrange
from django.utils.timezone import make_aware
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import VariableCost
from .forms import VariableCostForm
from django.db.models import Sum
from django.contrib import messages
from django.views.decorators.http import require_POST


@login_required
def variablecosts_list(request, year=None, month=None):
    today = date.today()

    if year is None or month is None:
        year = today.year
        month = today.month

    # 表示対象月の開始・終了日
    start_date = date(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date(year, month, last_day)

    # 月のフィルタで取得
    entries = VariableCost.objects.filter(purchase_date__range=(start_date, end_date)).order_by('purchase_date')


    # 合計額と費目ごとの合計を追加
    total_amount = entries.aggregate(total=Sum('amount'))['total'] or 0
    # ※ここが修正点：cost_itemごとにまとめる（entriesではなくVariableCostから直接）
    cost_item_totals = (VariableCost.objects
                        .filter(purchase_date__range=(start_date, end_date))
                        .values('cost_item__name')
                        .annotate(total=Sum('amount'))
                        .order_by('cost_item__id'))

    # ナビゲーション用の前月・次月
    prev_month = (start_date - timedelta(days=1)).replace(day=1)
    next_month = (end_date + timedelta(days=1)).replace(day=1)

    # 翌月が未来だったら None にする
    if next_month > today.replace(day=1):
        next_month = None

    return render(request, 'variablecosts/list.html', {
        'entries': entries,
        'year': year,
        'month': month,
        'prev_month': prev_month,
        'next_month': next_month,
        'total_amount': total_amount,
        'cost_item_totals': cost_item_totals,
    })

@login_required
def variablecosts_regist(request):
    if request.method == 'POST':
        form = VariableCostForm(request.POST)
        if form.is_valid():
            form.save(commit=True)
            return redirect('variablecosts:list')
    else:
        form = VariableCostForm()
    return render(request, 'variablecosts/regist.html', {
        'form': form
    })

@login_required
def variablecosts_edit(request, pk):
    entry = get_object_or_404(VariableCost, pk=pk)
    if request.method == 'POST':
        form = VariableCostForm(request.POST, instance=entry)
        if form.is_valid():
            form.save(commit=True)
            return redirect('variablecosts:list')
    else:
        form = VariableCostForm(instance=entry)
    return render(request, 'variablecosts/regist.html', {
        'form': form
    })

@login_required
def variablecosts_delete(request, pk):
    entry = get_object_or_404(VariableCost, pk=pk)
    if request.method == "POST":
        entry.delete()
        return redirect('variablecosts:list')
    return render(request, 'variablecosts/delete_confirm.html', {
        'entry': entry
    })

@login_required
@require_POST
def clear_payer(request, payer_name):
    updated_count = VariableCost.objects.filter(payer__name=payer_name).update(payer=None)
    messages.success(request, f"{payer_name} さんの立替データ（{updated_count}件）をクリアしました。")
    return redirect('core:home')