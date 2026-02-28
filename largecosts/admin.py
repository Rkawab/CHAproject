from django.contrib import admin
from .models import LargeCost


@admin.register(LargeCost)
class LargeCostAdmin(admin.ModelAdmin):
    list_display = ("purchase_date", "description", "amount", "cost_item", "payer")
    list_filter = ("purchase_date", "cost_item")
    search_fields = ("description",)
