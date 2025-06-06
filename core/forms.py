from django import forms
from .models import Budget

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'amount']
        widgets = {
            'category': forms.HiddenInput(),  # 編集時にカテゴリを隠す（固定費 or 変動費）
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
        }
