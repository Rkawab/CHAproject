from django import forms
from django.utils import timezone
from .models import PrivateVariableCost, PrivateFixedCost


class PrivateVariableCostForm(forms.ModelForm):
    """個人変動費フォーム（userはビュー側でURLから注入するため除外）"""

    class Meta:
        model = PrivateVariableCost
        fields = ["purchase_date", "amount", "cost_item", "description"]
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 新規登録時は購入日の初期値を今日に設定
        if not self.instance.pk:
            self.fields["purchase_date"].initial = timezone.localdate()
        # 費目を「その他」末尾にソート（既存パターン踏襲）
        from core.models import CostItem

        self.fields["cost_item"].queryset = CostItem.objects.extra(
            select={"custom_order": "CASE WHEN name = %s THEN 1 ELSE 0 END"},
            select_params=["その他"],
            order_by=["custom_order", "id"],
        )


class PrivateFixedCostForm(forms.ModelForm):
    """個人固定費フォーム（userはビュー側でURLから注入するため除外）"""

    class Meta:
        model = PrivateFixedCost
        fields = [
            "year",
            "month",
            "salary",
            "deduction",
            "subscriptions",
        ]

    def __init__(self, *args, **kwargs):
        # payer は重複バリデーションに使う（フォームフィールドには出さない）
        self.payer = kwargs.pop("payer", None)
        super().__init__(*args, **kwargs)
        # 新規作成時は当月を初期値にする
        if not self.instance.pk:
            today = timezone.localdate()
            self.fields["year"].initial = today.year
            self.fields["month"].initial = today.month
        # 各費目は任意入力
        for field_name in ["salary", "deduction", "subscriptions"]:
            self.fields[field_name].required = False

    def clean(self):
        cleaned_data = super().clean()
        year = cleaned_data.get("year")
        month = cleaned_data.get("month")
        # 同一Payer・同一年月の重複登録チェック
        if year and month and self.payer:
            qs = PrivateFixedCost.objects.filter(
                user=self.payer, year=year, month=month
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("month", f"{year}年{month}月のデータは既に存在します。")
        return cleaned_data
