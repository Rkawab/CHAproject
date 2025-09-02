from django import forms
from django.utils import timezone
from .models import FixedCost

class FixedCostForm(forms.ModelForm):
    class Meta:
        model = FixedCost
        fields = ['year', 'month', 'rent', 'water', 'electricity', 'gas', 'internet', 'subscriptions']
        widgets = {
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'month': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 12}),
            'rent': forms.NumberInput(attrs={'class': 'form-control'}),
            'water': forms.NumberInput(attrs={'class': 'form-control'}),
            'electricity': forms.NumberInput(attrs={'class': 'form-control'}),
            'gas': forms.NumberInput(attrs={'class': 'form-control'}),
            'internet': forms.NumberInput(attrs={'class': 'form-control'}),
            'subscriptions': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # インスタンスがなければ（新規作成時）、現在の年月をセット
        if not self.instance.pk:
            today = timezone.localdate()
            self.fields['year'].initial = today.year
            self.fields['month'].initial = today.month

        # 任意項目のラベルを調整
        for field_name in ['rent', 'water', 'electricity', 'gas', 'internet', 'subscriptions']:
            self.fields[field_name].required = False

        # デフォルトの値を設定
        self.fields['rent'].initial = 130000
        self.fields['internet'].initial = 5000

    def clean(self):
        cleaned_data = super().clean()
        year = cleaned_data.get('year')
        month = cleaned_data.get('month')

        # 年月の検証
        if year and month:
            # 年の検証
            if year < 2000 or year > 2100:
                self.add_error('year', '有効な年（2000～2100）を入力してください。')

            # 月の検証
            if month < 1 or month > 12:
                self.add_error('month', '有効な月（1～12）を入力してください。')

            # 重複チェック
            if self.instance.pk:  # 既存レコードの更新時
                existing = FixedCost.objects.filter(year=year, month=month).exclude(pk=self.instance.pk).exists()
            else:  # 新規作成時
                existing = FixedCost.objects.filter(year=year, month=month).exists()

            if existing:
                self.add_error('month', f'{year}年{month}月のデータは既に存在します。')

        return cleaned_data
