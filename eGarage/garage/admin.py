# ─────────────────────────────────────────────
#  eGarage – admin.py
# ─────────────────────────────────────────────
 
from django.contrib import admin
from .models import (
    ServiceProvider,
    CustomerProfile,
    Services,
    Bookings,
    Payments,
    Invoice,
    Review,
    Notification,
)
 
 
# Register your models here.
 
admin.site.register(ServiceProvider)
admin.site.register(CustomerProfile)
admin.site.register(Services)
admin.site.register(Bookings)
admin.site.register(Payments)
admin.site.register(Invoice)
admin.site.register(Review)
admin.site.register(Notification)