from django.contrib import admin
from core.models import Payer, CostItem
from .models import VariableCost

admin.site.register(CostItem)
admin.site.register(Payer)
admin.site.register(VariableCost)
