from django.contrib import admin
from .models import (
    PrivateVariableCost,
    PrivateFixedCost,
    PrivateAnnualInfo,
    PrivateSubscription,
)

admin.site.register(PrivateVariableCost)
admin.site.register(PrivateFixedCost)
admin.site.register(PrivateAnnualInfo)
admin.site.register(PrivateSubscription)
