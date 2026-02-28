from django import forms
from .models import Budget, CreditCard, PaymentItem


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ["category", "amount"]
        widgets = {
            "category": forms.HiddenInput(),  # 編集時にカテゴリを隠す（固定費 or 変動費）
            "amount": forms.NumberInput(attrs={"class": "form-control"}),
        }


class CreditCardForm(forms.ModelForm):
    class Meta:
        model = CreditCard
        fields = ["name", "owner", "note"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "owner": forms.Select(attrs={"class": "form-select"}),
            "note": forms.TextInput(attrs={"class": "form-control"}),
        }


class PaymentItemForm(forms.ModelForm):
    class Meta:
        model = PaymentItem
        fields = ["name", "card", "memo", "sort_order"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "card": forms.Select(attrs={"class": "form-select"}),
            "memo": forms.TextInput(attrs={"class": "form-control"}),
            "sort_order": forms.NumberInput(attrs={"class": "form-control"}),
        }
