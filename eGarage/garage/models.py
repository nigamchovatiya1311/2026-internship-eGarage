# ─────────────────────────────────────────────
#  eGarage – models.py
#  User model is imported from core app
# ─────────────────────────────────────────────

from django.db import models
from core.models import User   # ← your existing User from core app


# ──────────────────────────────────────────────
#  CHOICES
# ──────────────────────────────────────────────

APPROVAL_STATUS_CHOICES = (
    ('pending',  'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
)

VEHICLE_TYPE_CHOICES = (
    ('car',  'Car'),
    ('bike', 'Bike'),
)

BOOKING_STATUS_CHOICES = (
    ('pending',     'Pending'),
    ('confirmed',   'Confirmed'),
    ('in_progress', 'In Progress'),
    ('completed',   'Completed'),
    ('cancelled',   'Cancelled'),
)

PAYMENT_STATUS_CHOICES = (
    ('pending',   'Pending'),
    ('completed', 'Completed'),
    ('failed',    'Failed'),
    ('refunded',  'Refunded'),
)

PAYMENT_METHOD_CHOICES = (
    ('cash',   'Cash'),
    ('card',   'Card'),
    ('online', 'Online'),
)

NOTIFICATION_TYPE_CHOICES = (
    ('booking_confirmed',  'Booking Confirmed'),
    ('booking_cancelled',  'Booking Cancelled'),
    ('payment_received',   'Payment Received'),
    ('service_completed',  'Service Completed'),
    ('general',            'General'),
)


# ──────────────────────────────────────────────
#  1. SERVICE PROVIDER
#     One-to-One with User (role = service_provider)
# ──────────────────────────────────────────────

class ServiceProvider(models.Model):
    providerId     = models.AutoField(primary_key=True)
    user           = models.OneToOneField(
                         User,
                         on_delete=models.CASCADE,
                         related_name='service_provider_profile'
                     )
    garageName     = models.CharField(max_length=100)
    description    = models.TextField(blank=True, null=True)
    garageImage    = models.ImageField(upload_to='garage_images/', null=True, blank=True)
    location       = models.CharField(max_length=100)
    latitude       = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude      = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    openingTime    = models.TimeField()
    closingTime    = models.TimeField()
    rating         = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    approvalStatus = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='pending')

    class Meta:
        db_table = "serviceprovider"

    def __str__(self):
        return self.garageName


# ──────────────────────────────────────────────
#  2. CUSTOMER PROFILE
#     One-to-One with User (role = customer)
# ──────────────────────────────────────────────

class CustomerProfile(models.Model):
    customerId    = models.AutoField(primary_key=True)
    user          = models.OneToOneField(
                        User,
                        on_delete=models.CASCADE,
                        related_name='customer_profile'
                    )
    vehicleType   = models.CharField(max_length=10, choices=VEHICLE_TYPE_CHOICES, blank=True, default='car')
    vehicleNumber = models.CharField(max_length=20, blank=True, default='')
    vehicleModel  = models.CharField(max_length=50, blank=True, default='')
    vehicleYear   = models.IntegerField(null=True, blank=True)
    vehicleColor  = models.CharField(max_length=30, null=True, blank=True)
    extraVehicles = models.TextField(blank=True, default='')   # stores extra vehicles as JSON

    class Meta:
        db_table = "customer_profile"

    def __str__(self):
        return f"{self.user.email} – {self.vehicleNumber}"


# ──────────────────────────────────────────────
#  3. SERVICES
# ──────────────────────────────────────────────

class Services(models.Model):
    serviceId          = models.AutoField(primary_key=True)
    providerId         = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE, related_name='services')
    serviceName        = models.CharField(max_length=100)
    serviceDescription = models.TextField()
    servicePrice       = models.DecimalField(max_digits=10, decimal_places=2)
    estimatedDuration  = models.IntegerField(help_text="Duration in minutes", null=True, blank=True)
    isAvailable        = models.BooleanField(default=True)

    class Meta:
        db_table = "services"

    def __str__(self):
        return self.serviceName


# ──────────────────────────────────────────────
#  4. BOOKINGS
# ──────────────────────────────────────────────

class Bookings(models.Model):
    bookingId     = models.AutoField(primary_key=True)
    customer      = models.ForeignKey(
                        CustomerProfile,
                        on_delete=models.CASCADE,
                        related_name='bookings'
                    )
    provider      = models.ForeignKey(
                        ServiceProvider,
                        on_delete=models.CASCADE,
                        related_name='bookings'
                    )
    service       = models.ForeignKey(
                        Services,
                        on_delete=models.CASCADE,
                        related_name='bookings'
                    )
    bookingDate   = models.DateField()
    bookingTime   = models.TimeField(null=True, blank=True)
    notes         = models.TextField(blank=True, null=True)
    bookingStatus = models.CharField(max_length=20, choices=BOOKING_STATUS_CHOICES, default='pending')
    createdAt     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bookings"

    def __str__(self):
        return f"Booking #{self.bookingId} – {self.customer.user.email}"


# ──────────────────────────────────────────────
#  5. PAYMENTS
# ──────────────────────────────────────────────

class Payments(models.Model):
    paymentId     = models.AutoField(primary_key=True)
    booking       = models.OneToOneField(
                        Bookings,
                        on_delete=models.CASCADE,
                        related_name='payment'
                    )
    amount        = models.DecimalField(max_digits=10, decimal_places=2)
    paymentMethod = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    paymentStatus = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    transactionId = models.CharField(max_length=100, null=True, blank=True)
    paymentDate   = models.DateTimeField()

    class Meta:
        db_table = "payments"

    def __str__(self):
        return f"Payment #{self.paymentId} – {self.paymentStatus}"


# ──────────────────────────────────────────────
#  6. INVOICE
# ──────────────────────────────────────────────

class Invoice(models.Model):
    invoiceId      = models.AutoField(primary_key=True)
    booking        = models.OneToOneField(
                         Bookings,
                         on_delete=models.CASCADE,
                         related_name='invoice'
                     )
    payment        = models.ForeignKey(
                         Payments,
                         on_delete=models.SET_NULL,
                         null=True,
                         blank=True,
                         related_name='invoices'
                     )
    invoiceNumber  = models.CharField(max_length=20, unique=True)
    invoiceDate    = models.DateField()
    totalAmount    = models.DecimalField(max_digits=10, decimal_places=2)
    taxAmount      = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discountAmount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        db_table = "invoice"

    def __str__(self):
        return self.invoiceNumber


# ──────────────────────────────────────────────
#  7. REVIEW  (one review per booking)
# ──────────────────────────────────────────────

class Review(models.Model):
    reviewId  = models.AutoField(primary_key=True)
    booking   = models.OneToOneField(
                    Bookings,
                    on_delete=models.CASCADE,
                    related_name='review'
                )
    customer  = models.ForeignKey(
                    CustomerProfile,
                    on_delete=models.CASCADE,
                    related_name='reviews'
                )
    provider  = models.ForeignKey(
                    ServiceProvider,
                    on_delete=models.CASCADE,
                    related_name='reviews'
                )
    rating    = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])   # 1 to 5 stars
    comment   = models.TextField(blank=True, null=True)
    createdAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "review"

    def __str__(self):
        return f"Review #{self.reviewId} – {self.rating} stars"


# ──────────────────────────────────────────────
#  8. NOTIFICATION
# ──────────────────────────────────────────────

class Notification(models.Model):
    notificationId   = models.AutoField(primary_key=True)
    user             = models.ForeignKey(
                           User,
                           on_delete=models.CASCADE,
                           related_name='notifications'
                       )
    notificationType = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES)
    title            = models.CharField(max_length=100)
    message          = models.TextField()
    isRead           = models.BooleanField(default=False)
    createdAt        = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notification"

    def __str__(self):
        return f"{self.title} → {self.user.email}"