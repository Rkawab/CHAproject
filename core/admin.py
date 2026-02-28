from django.contrib import admin
from .models import Budget, CreditCard, PaymentItem


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("category", "amount")
    list_filter = ("category",)


@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "note")
    list_filter = ("owner",)
    search_fields = ("name", "owner__name")
    ordering = ("owner__name", "name")


@admin.register(PaymentItem)
class PaymentItemAdmin(admin.ModelAdmin):
    list_display = ("name", "card", "card_owner", "sort_order", "memo")
    list_filter = ("card__owner", "card")
    search_fields = ("name", "card__name", "card__owner__name", "memo")
    ordering = ("sort_order", "name")
    autocomplete_fields = ("card",)  # 便利（件数が増えた時に効く）

    def card_owner(self, obj):
        return obj.card.owner.name if obj.card else "-"

    card_owner.short_description = "所有者"
