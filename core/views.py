from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from finance.models import HouseholdAccount
from django.db.models import Sum
from datetime import datetime


# ホーム画面を表示するビュー
@login_required # ログインが成功した後でしか実行されないビュー
def home(request):
    today = now()
    first_day = today.replace(day=1)

    # 今月の出費（購入日が今月のデータ）
    monthly_entries = HouseholdAccount.objects.filter(purchase_date__gte=first_day, purchase_date__lte=today)

    # 今月の出費額の合計
    total_amount = monthly_entries.aggregate(total=Sum('amount'))['total'] or 0

    # 費目ごとの合計
    cost_item_totals = monthly_entries.values('cost_item__name').annotate(total=Sum('amount'))

    # 立替者ごとの合計
    payer_totals = monthly_entries.filter(payer__isnull=False)\
        .values('payer__name')\
        .annotate(total=Sum('amount'))\
        .order_by('payer__name')

    return render(request, 'home.html', {
        'total_amount': total_amount,
        'cost_item_totals': cost_item_totals,
        'payer_totals': payer_totals,  # ← 追加
    })
        # render(リクエスト情報, 表示するテンプレート, {HTMLで使用するデータ})