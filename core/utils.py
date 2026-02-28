def sort_cost_items_with_other_last(raw_queryset):
    """「その他」を最後に表示する順序で費目合計リストを並び替え"""
    cost_item_totals = []
    other_item = None
    for item in raw_queryset:
        if item["cost_item__name"] == "その他":
            other_item = item
        else:
            cost_item_totals.append(item)

    # 「その他」を最後に追加
    if other_item:
        cost_item_totals.append(other_item)

    return cost_item_totals


def build_available_months(min_date, max_date):
    """月選択プルダウン用の候補リストを生成（min_date〜max_dateの範囲）"""
    cur = min_date.replace(day=1)
    end = max_date.replace(day=1)
    available_months = []
    safe_guard = 0  # 念のため20年(240ヶ月)で上限
    while cur <= end and safe_guard < 240:
        available_months.append({"year": cur.year, "month": cur.month})
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)
        safe_guard += 1

    return available_months
