from datetime import timedelta
from calendar import monthrange
from django.utils import timezone
from django.utils.timezone import make_aware
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import VariableCost
from .forms import VariableCostForm
from django.db.models import Sum, Min, Max  # 月選択プルダウン用に最小・最大日付を集計するため Min/Max を追加
from django.contrib import messages
from django.views.decorators.http import require_POST


@login_required
def variablecosts_list(request, year=None, month=None):
    today = timezone.localdate()

    if year is None or month is None:
        year = today.year
        month = today.month

    # 表示対象月の開始・終了日
    start_date = today.replace(year=year, month=month, day=1)
    _, last_day = monthrange(year, month)
    end_date = start_date.replace(day=last_day)

    # 月のフィルタで取得
    entries = VariableCost.objects.filter(purchase_date__range=(start_date, end_date)).order_by('purchase_date')


    # 合計額と費目ごとの合計を追加
    total_amount = entries.aggregate(total=Sum('amount'))['total'] or 0
    # ※ここが修正点：cost_itemごとにまとめる（「その他」を最後に表示）
    cost_item_totals_raw = (VariableCost.objects
                            .filter(purchase_date__range=(start_date, end_date))
                            .values('cost_item__name', 'cost_item__id')
                            .annotate(total=Sum('amount'))
                            .order_by('cost_item__id'))
                            
    # Pythonで「その他」を最後に並び替え
    cost_item_totals = []
    other_item = None
    for item in cost_item_totals_raw:
        if item['cost_item__name'] == 'その他':
            other_item = item
        else:
            cost_item_totals.append(item)
    
    # 「その他」を最後に追加
    if other_item:
        cost_item_totals.append(other_item)

    # ナビゲーション用の前月・次月
    prev_month = (start_date - timedelta(days=1)).replace(day=1)
    next_month = (end_date + timedelta(days=1)).replace(day=1)

    # 翌月が未来だったら None にする
    if next_month > today.replace(day=1):
        next_month = None

    # 月選択プルダウンに表示する候補の生成
    # ・DBに保存されている変動費データの中で最も古い日付〜最新の日付を取得
    # ・最新は当月を超えないように制限（翌月ボタンと挙動を合わせる）
    agg = VariableCost.objects.aggregate(min_date=Min('purchase_date'), max_date=Max('purchase_date'))
    min_date = agg['min_date'] or start_date
    max_date = agg['max_date'] or start_date
    if max_date > today:
        max_date = today

    # 各月の1日へ正規化して、月単位のリストを組み立てる
    cur = min_date.replace(day=1)
    end = max_date.replace(day=1)
    available_months = []
    # 念のため無限ループ防止のガード（最大20年分）
    safe_guard = 0
    while cur <= end and safe_guard < 240:  # 念のため20年分に上限
        available_months.append({
            'year': cur.year,
            'month': cur.month,
        })
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)
        safe_guard += 1

    # データが全く無い場合でも、画面表示中の年月は少なくとも1件として候補に入れる
    if not available_months:
        available_months = [{
            'year': start_date.year,
            'month': start_date.month,
        }]

    return render(request, 'variablecosts/list.html', {
        'entries': entries,
        'year': year,
        'month': month,
        'prev_month': prev_month,
        'next_month': next_month,
        'total_amount': total_amount,
        'cost_item_totals': cost_item_totals,
        'available_months': available_months,
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
