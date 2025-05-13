from django.contrib import admin
from .models import CostItem, Payer, HouseholdAccount

admin.site.register(CostItem)
admin.site.register(Payer)
admin.site.register(HouseholdAccount)
