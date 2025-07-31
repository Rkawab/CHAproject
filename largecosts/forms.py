from django import forms
from .models import LargeCost
from core.models import CostItem
from django.utils import timezone

class LargeCostForm(forms.ModelForm):
    class Meta:
        model = LargeCost
        fields = ['purchase_date', 'amount', 'cost_item', 'description', 'payer']
        labels = {
            'purchase_date': '購入日',
            'amount': '金額',
            'cost_item': '費目',
            'description': '名称',
            'payer': '立替者',
        }
        widgets = {
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['purchase_date'].initial = timezone.now().date()
        
        # 費目の選択肢を「その他」を最後にする順序で設定
        self.fields['cost_item'].queryset = CostItem.objects.extra(
            select={'custom_order': 'CASE WHEN name = %s THEN 1 ELSE 0 END'},
            select_params=['その他'],
            order_by=['custom_order', 'id']
        )
