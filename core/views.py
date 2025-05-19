from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from variablecosts.models import VariableCost
from django.db.models import Sum
from datetime import datetime
from fixedcosts.models import FixedCost
from collections import OrderedDict



# ホーム画面を表示するビュー
@login_required # ログインが成功した後でしか実行されないビュー
def home(request):
    today = now()
    first_day = today.replace(day=1)

    # 今月の出費（購入日が今月のデータ）
    monthly_entries = VariableCost.objects.filter(purchase_date__gte=first_day, purchase_date__lte=today)

    # 今月の出費額の合計
    total_variable_cost = monthly_entries.aggregate(total=Sum('amount'))['total'] or 0

    # 費目ごとの合計
    cost_item_totals = monthly_entries.values('cost_item__name').annotate(total=Sum('amount'))

    # 立替者ごとの合計
    payer_totals = monthly_entries.filter(payer__isnull=False)\
        .values('payer__name')\
        .annotate(total=Sum('amount'))\
        .order_by('payer__name')

    # 今月の固定費データを取得（FixedCost）
    year = today.year
    month = today.month
    fixed_cost = FixedCost.objects.filter(year=year, month=month).first()

    total_fixed_cost = 0
    missing_fixed_items = []

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

    return render(request, 'home.html', {
        'total_amount': total_amount,
        'cost_item_totals': cost_item_totals,
        'payer_totals': payer_totals,
        'total_variable_cost' : total_variable_cost,
        'total_fixed_cost' : total_fixed_cost,
        'missing_fixed_items': missing_fixed_items,
        'year': year,
        'month': month,
    })
        # render(リクエスト情報, 表示するテンプレート, {HTMLで使用するデータ})