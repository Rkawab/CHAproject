from django import forms
from django.utils import timezone
from .models import (
    PrivateVariableCost,
    PrivateFixedCost,
    PrivateAnnualInfo,
    PrivateSubscription,
)


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
            "savings",
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
        for field_name in ["salary", "deduction", "savings"]:
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


class PrivateAnnualInfoForm(forms.ModelForm):
    """個人年間情報フォーム（userはビュー側でURLから注入するため除外）"""

    class Meta:
        model = PrivateAnnualInfo
        fields = ["year", "summer_bonus", "winter_bonus"]

    def __init__(self, *args, **kwargs):
        self.payer = kwargs.pop("payer", None)
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["year"].initial = timezone.localdate().year
        self.fields["summer_bonus"].required = False
        self.fields["winter_bonus"].required = False

    def clean(self):
        cleaned_data = super().clean()
        year = cleaned_data.get("year")
        if year and self.payer:
            qs = PrivateAnnualInfo.objects.filter(user=self.payer, year=year)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error("year", f"{year}年の年間情報は既に存在します。")
        return cleaned_data


class PrivateSubscriptionForm(forms.ModelForm):
    """個人用サブスクフォーム（userはビュー側でURLから注入するため除外）"""

    class Meta:
        model = PrivateSubscription
        fields = [
            "name",
            "amount",
            "start_year",
            "start_month",
            "end_year",
            "end_month",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "start_year": forms.NumberInput(
                attrs={"class": "form-control", "min": 2000, "max": 2100}
            ),
            "start_month": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "max": 12}
            ),
            "end_year": forms.NumberInput(
                attrs={"class": "form-control", "min": 2000, "max": 2100}
            ),
            "end_month": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "max": 12}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            today = timezone.localdate()
            self.fields["start_year"].initial = today.year
            self.fields["start_month"].initial = today.month
        self.fields["end_year"].required = False
        self.fields["end_month"].required = False

    def clean(self):
        cleaned = super().clean()
        start_year = cleaned.get("start_year")
        start_month = cleaned.get("start_month")
        end_year = cleaned.get("end_year")
        end_month = cleaned.get("end_month")

        if (end_year is None) != (end_month is None):
            self.add_error(
                "end_month",
                "終了年と終了月は両方入力するか、両方空欄にしてください。",
            )

        if start_year and start_month and end_year and end_month:
            if (end_year, end_month) < (start_year, start_month):
                self.add_error("end_month", "終了年月は開始年月以降にしてください。")

        return cleaned
