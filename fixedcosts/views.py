from datetime import date
from calendar import monthrange
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import FixedCost
from .forms import FixedCostForm

@login_required
def fixedcosts_list(request, year=None, month=None):
    """固定費の月別一覧を表示"""
    today = date.today()

    # 年月が指定されていなければ、現在の年月を使用
    if year is None or month is None:
        year = today.year
        month = today.month

    # 指定された年月の固定費を取得
    try:
        fixed_cost = FixedCost.objects.get(year=year, month=month)
    except FixedCost.DoesNotExist:
        # 存在しない場合は新規作成
        fixed_cost = None

    # 前月・次月の固定費が存在するか確認
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1

    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    # 翌月が未来すぎる場合は制限
    future_limit = date(next_year, next_month, 1) > today.replace(day=1, month=today.month+1 if today.month < 12 else 1, year=today.year if today.month < 12 else today.year+1)

    # 前月・次月のデータ存在確認
    prev_exists = FixedCost.objects.filter(year=prev_year, month=prev_month).exists()
    next_exists = FixedCost.objects.filter(year=next_year, month=next_month).exists() if not future_limit else False
    
    # 総固定費
    total_cost = fixed_cost.get_total_cost() if fixed_cost else 0

    # 水道代の調整（2か月に1回）も fixed_cost がある場合だけ計算
    adjusted_water = None
    items = []

    if fixed_cost:
        if fixed_cost.water is not None:
            # 入力あり → 半額にして表示
            adjusted_water = fixed_cost.water // 2
        else:
            # 入力なし → 前月データから取得
            prev_month_fc = FixedCost.objects.filter(year=prev_year, month=prev_month).first()
            if prev_month_fc and prev_month_fc.water is not None:
                adjusted_water = prev_month_fc.water // 2

        # 合計の再計算（adjusted_water を使う）
        total_cost = sum(filter(None, [
            fixed_cost.rent,
            adjusted_water,
            fixed_cost.electricity,
            fixed_cost.gas,
            fixed_cost.internet,
            fixed_cost.subscriptions
        ]))

        items = [
            ('家賃', fixed_cost.rent, ''),
            ('水道代', adjusted_water, ''),
            ('電気代', fixed_cost.electricity, ''),
            ('ガス代', fixed_cost.gas, ''),
            ('ネット代', fixed_cost.internet, ''),
            ('サブスク代', fixed_cost.subscriptions, ''),
        ]

    return render(request, 'fixedcosts/list.html', {
        'fixed_cost': fixed_cost,
        'year': year,
        'month': month,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month if not future_limit else None,
        'next_year': next_year if not future_limit else None,
        'prev_exists': prev_exists,
        'next_exists': next_exists,
        'total_cost': total_cost,
        'adjusted_water': adjusted_water,
        'items': items,
    })

@login_required
def fixedcosts_edit(request, year=None, month=None):
    """固定費の編集"""
    today = date.today()
    
    # 年月が指定されていなければ、現在の年月を使用
    if year is None or month is None:
        year = today.year
        month = today.month
    
    # 指定された年月の固定費を取得または新規作成
    try:
        fixed_cost = FixedCost.objects.get(year=year, month=month)
    except FixedCost.DoesNotExist:
        fixed_cost = FixedCost(year=year, month=month)
    
    if request.method == 'POST':
        form = FixedCostForm(request.POST, instance=fixed_cost)
        if form.is_valid():
            form.save()
            messages.success(request, f"{year}年{month}月の固定費を保存しました。")
            return redirect('fixedcosts:list_by_month', year=year, month=month)
    else:
        form = FixedCostForm(instance=fixed_cost)
    
    return render(request, 'fixedcosts/edit.html', {
        'form': form,
        'year': year,
        'month': month,
        'is_new': not fixed_cost.pk,
    })

@login_required
def fixedcosts_delete(request, year, month):
    """固定費の削除"""
    fixed_cost = get_object_or_404(FixedCost, year=year, month=month)

    cost_items = {
        '家賃': fixed_cost.rent,
        '水道代': fixed_cost.water,
        '電気代': fixed_cost.electricity,
        'ガス代': fixed_cost.gas,
        'ネット代': fixed_cost.internet,
        'サブスク代': fixed_cost.subscriptions,
    }
    
    if request.method == "POST":
        fixed_cost.delete()
        messages.success(request, f"{year}年{month}月の固定費データを削除しました。")
        
        # 今月または前月にリダイレクト
        today = date.today()
        if today.year == year and today.month == month:
            # 削除したのが今月のデータの場合、前月に移動
            prev_month = month - 1 if month > 1 else 12
            prev_year = year if month > 1 else year - 1
            return redirect('fixedcosts:list', year=prev_year, month=prev_month)
        else:
            # それ以外は今月に移動
            return redirect('fixedcosts:list')
    
    return render(request, 'fixedcosts/delete_confirm.html', {
        'fixed_cost': fixed_cost,
        'cost_items': cost_items,
    })