from django.contrib import admin

from .models import *

# Register your models here.
admin.site.register(BusinessProfile)
admin.site.register(BusinessOffer)
admin.site.register(CustomerProfile)
admin.site.register(CustomerVisitCount)
admin.site.register(CustomerVisitHistory)
admin.site.register(SubscriptionPayment)