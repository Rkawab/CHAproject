from django.contrib import admin
from .models import PrivateVariableCost, PrivateFixedCost

admin.site.register(PrivateVariableCost)
admin.site.register(PrivateFixedCost)
