from django import forms
from django.utils import timezone
from .models import FixedCost, Subscription


class FixedCostForm(forms.ModelForm):
    class Meta:
        model = FixedCost
        fields = [
            "year",
            "month",
            "rent",
            "water",
            "electricity",
            "gas",
            "internet",
        ]
        widgets = {
            "year": forms.NumberInput(attrs={"class": "form-control"}),
            "month": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "max": 12}
            ),
            "rent": forms.NumberInput(attrs={"class": "form-control"}),
            "water": forms.NumberInput(attrs={"class": "form-control"}),
            "electricity": forms.NumberInput(attrs={"class": "form-control"}),
            "gas": forms.NumberInput(attrs={"class": "form-control"}),
            "internet": forms.NumberInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            today = timezone.localdate()
            self.fields["year"].initial = today.year
            self.fields["month"].initial = today.month

        for field_name in ["rent", "water", "electricity", "gas", "internet"]:
            self.fields[field_name].required = False

        self.fields["rent"].initial = 130000
        self.fields["internet"].initial = 5000

    def clean(self):
        cleaned_data = super().clean()
        year = cleaned_data.get("year")
        month = cleaned_data.get("month")

        if year and month:
            if year < 2000 or year > 2100:
                self.add_error("year", "有効な年（2000～2100）を入力してください。")

            if month < 1 or month > 12:
                self.add_error("month", "有効な月（1～12）を入力してください。")

            if self.instance.pk:
                existing = (
                    FixedCost.objects.filter(year=year, month=month)
                    .exclude(pk=self.instance.pk)
                    .exists()
                )
            else:
                existing = FixedCost.objects.filter(year=year, month=month).exists()

            if existing:
                self.add_error("month", f"{year}年{month}月のデータは既に存在します。")

        return cleaned_data


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
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
        ey = cleaned.get("end_year")
        em = cleaned.get("end_month")
        sy = cleaned.get("start_year")
        sm = cleaned.get("start_month")

        # 終了年月は両方入力 or 両方空欄
        if (ey is None) != (em is None):
            self.add_error("end_month", "終了年と終了月は両方入力するか、両方空欄にしてください。")

        # 開始 <= 終了
        if sy and sm and ey and em:
            if (ey, em) < (sy, sm):
                self.add_error("end_month", "終了年月は開始年月以降にしてください。")

        return cleaned
