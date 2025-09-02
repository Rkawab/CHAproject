from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.utils import timezone
from django.contrib import messages
from variablecosts.models import VariableCost
from django.db.models import Sum
from core.models import Budget
from datetime import datetime
from fixedcosts.models import FixedCost
from collections import OrderedDict
from .forms import BudgetForm



# ホーム画面を表示するビュー
@login_required # ログインが成功した後でしか実行されないビュー
def home(request):
    # ローカルタイムゾーン基準の日付で集計する
    today = timezone.localdate()
    first_day = today.replace(day=1)

    # 今月の出費（購入日が今月のデータ）
    monthly_entries = VariableCost.objects.filter(purchase_date__gte=first_day, purchase_date__lte=today)

    # 今月の出費額の合計
    total_variable_cost = monthly_entries.aggregate(total=Sum('amount'))['total'] or 0

    # 費目ごとの合計（「その他」を最後に表示）
    cost_item_totals_raw = monthly_entries.values('cost_item__name', 'cost_item__id').annotate(total=Sum('amount')).order_by('cost_item__id')
    
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

    # 立替金額合計(全期間)
    payer_totals = VariableCost.objects.filter(payer__isnull=False)\
        .values('payer__name')\
        .annotate(total=Sum('amount'))\
        .order_by('payer__name')

    # 今月の固定費データを取得（FixedCost）
    year = today.year
    month = today.month
    fixed_cost = FixedCost.objects.filter(year=year, month=month).first()

    total_fixed_cost = 0
    total_amount = total_variable_cost  # 初期値として変動費だけ
    missing_fixed_items = []

    # デフォルトの予算（固定費なしでも必要なため）
    budgets = {b.category: b.amount for b in Budget.objects.all()}
    fixed_budget = budgets.get('fixed', 0)
    variable_budget = budgets.get('variable', 0)
    total_budget = fixed_budget + variable_budget

    remaining_fixed = fixed_budget
    remaining_variable = variable_budget - total_variable_cost
    remaining_total = total_budget - total_variable_cost

    if fixed_cost:
        # 項目とラベルの対応（順序あり）
        items = OrderedDict([
            ('rent', '家賃'),
            ('electricity', '電気代'),
            ('gas', 'ガス代'),
            ('internet', 'ネット代'),
            ('subscriptions', 'サブスク代'),
            ('water', '水道代'),  # 注意：adjustedの判定にも使う
        ])

        # 水道代は半額で計算
        adjusted_water = fixed_cost.water if fixed_cost.water is not None else None
        if adjusted_water is None:
            # 前月から取得
            prev_month = month - 1 if month > 1 else 12
            prev_year = year if month > 1 else year - 1
            prev_fc = FixedCost.objects.filter(year=prev_year, month=prev_month).first()
            adjusted_water = prev_fc.water if prev_fc and prev_fc.water is not None else 0

        for attr, label in items.items():
            value = getattr(fixed_cost, attr)
            if value in (0, None):  # 0かNoneの場合
                if not (attr == 'water' and adjusted_water != 0):
                    missing_fixed_items.append(label)

        total_fixed_cost = (
            (fixed_cost.rent or 0) +
            (fixed_cost.electricity or 0) +
            (fixed_cost.gas or 0) +
            (fixed_cost.internet or 0) +
            (fixed_cost.subscriptions or 0) +
            (adjusted_water // 2)  # 水道代は半額
        )
        total_amount = total_variable_cost + total_fixed_cost

        # 予算データを取得
        budgets = {b.category: b.amount for b in Budget.objects.all()}
        fixed_budget = budgets.get('fixed', 0)
        variable_budget = budgets.get('variable', 0)
        total_budget = fixed_budget + variable_budget

        # 残金（予算 - 実支出）を計算
        remaining_fixed = fixed_budget - total_fixed_cost
        remaining_variable = variable_budget - total_variable_cost
        remaining_total = total_budget - total_amount


    return render(request, 'home.html', {
        'total_amount': total_amount,
        'cost_item_totals': cost_item_totals,
        'payer_totals': payer_totals,
        'total_variable_cost' : total_variable_cost,
        'total_fixed_cost' : total_fixed_cost,
        'missing_fixed_items': missing_fixed_items,
        'fixed_budget': fixed_budget,
        'variable_budget': variable_budget,
        'total_budget': total_budget,
        'remaining_fixed': remaining_fixed,
        'remaining_variable': remaining_variable,
        'remaining_total': remaining_total,
        'year': year,
        'month': month,
    })
        # render(リクエスト情報, 表示するテンプレート, {HTMLで使用するデータ})

@login_required
def edit_budget(request):
    budgets = {b.category: b for b in Budget.objects.all()}
    fixed_budget = budgets.get('fixed', Budget(category='fixed'))
    variable_budget = budgets.get('variable', Budget(category='variable'))

    if request.method == 'POST':
        fixed_form = BudgetForm(request.POST, instance=fixed_budget, prefix='fixed')
        variable_form = BudgetForm(request.POST, instance=variable_budget, prefix='variable')

        if fixed_form.is_valid() and variable_form.is_valid():
            fixed_form.save()
            variable_form.save()
            messages.success(request, '予算を更新しました。')
            return redirect('core:home')
    else:
        fixed_form = BudgetForm(instance=fixed_budget, prefix='fixed')
        variable_form = BudgetForm(instance=variable_budget, prefix='variable')

    return render(request, 'edit_budget.html', {
        'fixed_form': fixed_form,
        'variable_form': variable_form,
    })
