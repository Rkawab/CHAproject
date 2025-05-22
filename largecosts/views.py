from datetime import date, timedelta
from calendar import monthrange
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import LargeCost
from .forms import LargeCostForm

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

    return render(request, 'largecosts/list.html', {
        'entries': entries,
        'year': year,
        'month': month,
        'prev_month': prev_month,
        'next_month': next_month,
        'total_amount': total_amount,
        'cost_item_totals': cost_item_totals,
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
def clear_payer(request, payer_name):
    updated_count = LargeCost.objects.filter(payer__name=payer_name).update(payer=None)
    messages.success(request, f"{payer_name} さんの立替データ（{updated_count}件）をクリアしました。")
    return redirect('core:home')
