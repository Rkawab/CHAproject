from django.contrib import admin
from .models import FixedCost

@admin.register(FixedCost)
class FixedCostAdmin(admin.ModelAdmin):
    list_display = ('year', 'month', 'rent', 'water', 'electricity', 'gas', 'internet', 'subscriptions', 'get_total_cost')
    list_filter = ('year', 'month')
    search_fields = ('year', 'month')
    ordering = ('-year', '-month')
    
    def get_total_cost(self, obj):
        return obj.get_total_cost()
    get_total_cost.short_description = '合計金額'