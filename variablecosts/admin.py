from django.contrib import admin
from .models import CostItem, Payer, VariableCost

admin.site.register(CostItem)
admin.site.register(Payer)
admin.site.register(VariableCost)
