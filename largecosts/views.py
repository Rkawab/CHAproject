from datetime import date, timedelta
from calendar import monthrange
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Value
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import LargeCost
from core.models import Payer
from .forms import LargeCostForm
from decimal import Decimal  # 金額の精度対応のため
from django.db.models.functions import Coalesce




@login_required
def largecosts_list(request, year=None, month=None):
    today = date.today()
    if year is None or month is None:
        year = today.year
        month = today.month
    start_date = date(year, month, 1)
    _, last_day = monthrange(year, month)
    end_date = date(year, month, last_day)

    entries = LargeCost.objects.filter(purchase_date__range=(start_date, end_date)).order_by('purchase_date')
    total_amount = entries.aggregate(total=Sum('amount'))['total'] or 0
    cost_item_totals = (LargeCost.objects
                        .filter(purchase_date__range=(start_date, end_date))
                        .values('cost_item__name')
                        .annotate(total=Sum('amount'))
                        .order_by('cost_item__name'))

    prev_month = (start_date - timedelta(days=1)).replace(day=1)
    next_month = (end_date + timedelta(days=1)).replace(day=1)
    if next_month > today.replace(day=1):
        next_month = None

    payers = list(Payer.objects.filter(name__isnull=False).values_list('name', flat=True))

    # 全期間のpayer別合計
    payer_totals = list(LargeCost.objects
        .filter(payer__isnull=False)
        .values('payer__name')
        .annotate(total=Sum('amount'))
        .order_by('payer__name'))

    # 各Payerについて合計金額を取得（存在しない場合は0）
    raw_totals = LargeCost.objects.filter(payer__name__in=payers) \
        .values('payer__name') \
        .annotate(total=Coalesce(Sum('amount'), Value(0))) \
        .order_by('payer__name')

    # 辞書化して、足りないpayerは0で補完
    payer_totals_dict = {item['payer__name']: item['total'] for item in raw_totals}
    payer_totals = [{'payer__name': name, 'total': payer_totals_dict.get(name, 0)} for name in payers]


    settlement_info = None

    # 0でないpayerが1人以上いれば精算処理を行う
    if any(p['total'] != 0 for p in payer_totals):
        payer1, payer2 = payer_totals
        if payer1['total'] > payer2['total']:
            payer_from, payer_to = payer2, payer1
        else:
            payer_from, payer_to = payer1, payer2

        diff = abs(payer1['total'] - payer2['total']) / Decimal(2)
        settlement_info = {
            'payer_from': payer_from['payer__name'],
            'payer_to': payer_to['payer__name'],
            'amount': diff
        }

    return render(request, 'largecosts/list.html', {
        'entries': entries,
        'year': year,
        'month': month,
        'payer_totals': payer_totals,
        'prev_month': prev_month,
        'next_month': next_month,
        'total_amount': total_amount,
        'cost_item_totals': cost_item_totals,
        'settlement_info': settlement_info,
    })

@login_required
def largecosts_regist(request):
    if request.method == 'POST':
        form = LargeCostForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('largecosts:list')
    else:
        form = LargeCostForm()
    return render(request, 'largecosts/regist.html', {'form': form})

@login_required
def largecosts_edit(request, pk):
    entry = get_object_or_404(LargeCost, pk=pk)
    if request.method == 'POST':
        form = LargeCostForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            return redirect('largecosts:list')
    else:
        form = LargeCostForm(instance=entry)
    return render(request, 'largecosts/regist.html', {'form': form})

@login_required
def largecosts_delete(request, pk):
    entry = get_object_or_404(LargeCost, pk=pk)
    if request.method == "POST":
        entry.delete()
        return redirect('largecosts:list')
    return render(request, 'largecosts/delete_confirm.html', {'entry': entry})

@login_required
@require_POST
def clear_settlement(request):
    updated_count = LargeCost.objects.filter(payer__isnull=False).update(payer=None)
    messages.success(request, f"立替データ（{updated_count}件）をクリアしました。")
    return redirect('largecosts:list')
