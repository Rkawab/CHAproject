from django import forms
from .models import HouseholdAccount
from django.utils import timezone


class HouseholdAccountForm(forms.ModelForm):
    class Meta:
        model = HouseholdAccount
        fields = ['purchase_date', 'amount', 'cost_item', 'description', 'used_shared_card', 'payer']
        labels = {
            'purchase_date': '購入日',
            'amount': '金額',
            'cost_item': '費目',
            'description': '名称',
            'used_shared_card': '共用カード使用',
            'payer': '立替者',
        }
        widgets = {
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),   # 購入日を日付入力に
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['purchase_date'].initial = timezone.now().date()
            self.fields['used_shared_card'].initial = True  # 共用カードをデフォルトでチェック

    def save(self, commit=False):
        instance = super().save(commit=False)
        # 処理がある場合は追加
        if commit:
            instance.save()
        return instance