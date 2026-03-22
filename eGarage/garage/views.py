from .decorators import role_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Avg, Count
from django.db.models.functions import TruncMonth
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Avg as AvgF
import csv
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import logout
from datetime import date, timedelta
from calendar import month_abbr
import uuid

# ── Import your models ──────────────────────────────────────
from core.models import User
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


# ============================================================
#  ADMIN REDIRECT
# ============================================================
@role_required(allowed_roles=["admin"])
def admindashboard(request):
    return redirect('admin_overview')


# ============================================================
#  SHARED BASE CONTEXT  (sidebar badges — live counts)
# ============================================================
def get_base_context(request):
    return {
        'total_users':          User.objects.count(),
        'pending_providers':    ServiceProvider.objects.filter(approvalStatus='pending').count(),
        'new_bookings':         Bookings.objects.filter(bookingStatus='pending').count(),
        'unread_notifications': Notification.objects.filter(isRead=False).count(),
        'open_disputes':        0,   # No Dispute model yet — update when added

        'notifications_list':   Notification.objects.filter(isRead=False).order_by('-createdAt')[:5],
    }


# ============================================================
#  1. OVERVIEW  —  /admin-panel/
# ============================================================
@role_required(allowed_roles=["admin"])
def overview(request):
    today = date.today()

    # ── stat cards ─────────────────────────────────────────
    total_users     = User.objects.count()
    total_providers = ServiceProvider.objects.count()
    total_bookings  = Bookings.objects.count()
    monthly_revenue = (
        Payments.objects
        .filter(paymentStatus='completed', paymentDate__month=today.month, paymentDate__year=today.year)
        .aggregate(total=Sum('amount'))['total'] or 0
    )

    # ── booking status breakdown ────────────────────────────
    status_counts = Bookings.objects.aggregate(
        completed  = Count('bookingId', filter=Q(bookingStatus='completed')),
        in_progress= Count('bookingId', filter=Q(bookingStatus='in_progress')),
        pending    = Count('bookingId', filter=Q(bookingStatus='pending')),
        cancelled  = Count('bookingId', filter=Q(bookingStatus='cancelled')),
    )

    # ── recent 5 bookings ───────────────────────────────────
    recent_bookings = (
        Bookings.objects
        .select_related('customer__user', 'service', 'provider')
        .order_by('-createdAt')[:5]
    )

    # Attach a display amount from related payment if present
    enriched_bookings = []
    for b in recent_bookings:
        amount = 0
        if hasattr(b, 'payment'):
            amount = b.payment.amount
        enriched_bookings.append({
            'id':       b.bookingId,
            'customer': b.customer.user,
            'service':  b.service,
            'provider': b.provider,
            'date':     b.bookingDate,
            'amount':   amount,
            'status':   b.bookingStatus,
        })

    context = {
        **get_base_context(request),
        'active_section':       'overview',
        'today':                today.strftime('%d %b %Y'),

        # stat cards
        'total_users':          total_users,
        'total_bookings':       total_bookings,
        'total_providers':      total_providers,
        'monthly_revenue':      monthly_revenue,

        # donut chart
        'completed_bookings':   status_counts['completed'],
        'inprogress_bookings':  status_counts['in_progress'],
        'pending_bookings':     status_counts['pending'],
        'cancelled_bookings':   status_counts['cancelled'],

        # table
        'recent_bookings':      enriched_bookings,
    }
    return render(request, 'garage/Admin/overview.html', context)


# ============================================================
#  2. MANAGE USERS  —  /admin-panel/users/
# ============================================================
@role_required(allowed_roles=["admin"])
def manage_users(request):
    q      = request.GET.get('q', '').strip()
    role   = request.GET.get('role', 'all')
    status = request.GET.get('status', '')
    page   = request.GET.get('page', 1)

    # qs = User.objects.order_by('-date_joined')
    qs = User.objects.order_by('-created_at')


    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)  |
            Q(email__icontains=q)
        )
    if role not in ('', 'all'):
        qs = qs.filter(role=role)
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'blocked':
        qs = qs.filter(is_active=False)

    # Attach a colour to each user for the avatar
    COLORS = ['#e8560a', '#1e3a5f', '#16a34a', '#7c3aed', '#f9a825', '#dc2626']
    users_with_color = []
    for i, u in enumerate(qs):
        u.avatar_color = COLORS[i % len(COLORS)]
        u.status       = 'active' if u.is_active else 'blocked'
        users_with_color.append(u)

    paginator  = Paginator(users_with_color, 20)
    users_page = paginator.get_page(page)

    context = {
        **get_base_context(request),
        'active_section':  'users',
        'users':           users_page,
        'total_users':     User.objects.count(),
        'total_customers': User.objects.filter(role='customer').count(),
        'total_providers': User.objects.filter(role='service_provider').count(),
        'total_admins':    User.objects.filter(is_staff=True).count(),
    }
    return render(request, 'garage/Admin/users.html', context)


# ── Block a user ─────────────────────────────────────────────
@role_required(allowed_roles=["admin"])
def block_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.is_active = False
    user.save()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, f'{user.get_full_name()} blocked.')
    return redirect('admin_users')


# ── Unblock a user ───────────────────────────────────────────
@role_required(allowed_roles=["admin"])
def unblock_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.is_active = True
    user.save()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, f'{user.get_full_name()} unblocked.')
    return redirect('admin_users')


# ── Approve a pending user ───────────────────────────────────
@role_required(allowed_roles=["admin"])
def approve_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    user.is_active = True
    user.save()
    messages.success(request, f'{user.get_full_name()} approved successfully.')
    return redirect('admin_users')


# ── Add user ─────────────────────────────────────────────────
@role_required(allowed_roles=["admin"])
def add_user(request):
    if request.method == 'POST':
        messages.success(request, 'User created successfully.')
        return redirect('admin_users')
    context = {**get_base_context(request), 'active_section': 'users'}
    return render(request, 'garage/Admin/add_user.html', context)


# ============================================================
#  3. SERVICE PROVIDERS  —  /admin-panel/providers/
# ============================================================
@role_required(allowed_roles=["admin"])
def service_providers(request):
    q        = request.GET.get('q', '').strip()
    approval = request.GET.get('approval', 'all')
    page     = request.GET.get('page', 1)

    qs = ServiceProvider.objects.select_related('user').order_by('-providerId')

    if q:
        qs = qs.filter(
            Q(garageName__icontains=q)       |
            Q(location__icontains=q)          |
            Q(user__first_name__icontains=q)
        )
    if approval not in ('', 'all'):
        qs = qs.filter(approvalStatus=approval)

    # Attach helper attributes expected by the template
    for p in qs:
        p.garage_name     = p.garageName
        p.city            = p.location
        p.working_hours   = f"{p.openingTime.strftime('%I:%M %p')} – {p.closingTime.strftime('%I:%M %p')}"
        p.avg_rating      = p.rating
        p.approval_status = p.approvalStatus

    paginator      = Paginator(qs, 20)
    providers_page = paginator.get_page(page)

    stats = ServiceProvider.objects.aggregate(
        approved = Count('providerId', filter=Q(approvalStatus='approved')),
        pending  = Count('providerId', filter=Q(approvalStatus='pending')),
        rejected = Count('providerId', filter=Q(approvalStatus='rejected')),
        avg_r    = Avg('rating'),
    )

    context = {
        **get_base_context(request),
        'active_section': 'providers',
        'providers':      providers_page,
        'approved_count': stats['approved'],
        'pending_count':  stats['pending'],
        'rejected_count': stats['rejected'],
        'avg_rating':     round(stats['avg_r'] or 0, 1),
    }
    return render(request, 'garage/Admin/providers.html', context)


# ── Approve a provider ───────────────────────────────────────
@role_required(allowed_roles=["admin"])
def approve_provider(request, pk):
    provider = get_object_or_404(ServiceProvider, pk=pk)
    provider.approvalStatus = 'approved'
    provider.save()
    Notification.objects.create(
        user=provider.user,
        notificationType='general',
        title='Garage Approved',
        message=f'Your garage "{provider.garageName}" has been approved. You can now receive bookings.',
    )
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'garage_name': provider.garageName})
    messages.success(request, f'"{provider.garageName}" approved successfully.')
    return redirect('admin_providers')


# ── Reject / delete a provider ───────────────────────────────
@role_required(allowed_roles=["admin"])
def reject_provider(request, pk):
    provider = get_object_or_404(ServiceProvider, pk=pk)
    name = provider.garageName
    Notification.objects.create(
        user=provider.user,
        notificationType='general',
        title='Garage Application Rejected',
        message=f'Your garage "{name}" application has been rejected. Please contact support.',
    )
    provider.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, f'"{name}" removed.')
    return redirect('admin_providers')


# ============================================================
#  4. CUSTOMER PROFILES  —  /admin-panel/customers/
# ============================================================
@role_required(allowed_roles=["admin"])
def customer_profiles(request):
    q            = request.GET.get('q', '').strip()
    vehicle_type = request.GET.get('type', 'all')

    qs = CustomerProfile.objects.select_related('user').order_by('user__first_name')

    if q:
        qs = qs.filter(
            Q(user__first_name__icontains=q) |
            Q(vehicleNumber__icontains=q)    |
            Q(vehicleModel__icontains=q)
        )
    if vehicle_type not in ('', 'all'):
        qs = qs.filter(vehicleType=vehicle_type)

    # Map camelCase model fields → snake_case names the template uses
    for cp in qs:
        cp.vehicle_type   = cp.vehicleType
        cp.vehicle_number = cp.vehicleNumber
        cp.vehicle_model  = cp.vehicleModel
        cp.vehicle_year   = cp.vehicleYear
        cp.vehicle_color  = cp.vehicleColor

    context = {
        **get_base_context(request),
        'active_section':   'customers',
        'customer_profiles': qs,
    }
    return render(request, 'garage/Admin/customers.html', context)


# ============================================================
#  5. SERVICES  —  /admin-panel/services/
# ============================================================
@role_required(allowed_roles=["admin"])
def services(request):
    q        = request.GET.get('q', '').strip()
    provider = request.GET.get('provider', '')
    status   = request.GET.get('status', '')

    qs = Services.objects.select_related('providerId').order_by('serviceName')

    if q:
        qs = qs.filter(
            Q(serviceName__icontains=q) |
            Q(serviceDescription__icontains=q)
        )
    if provider:
        qs = qs.filter(providerId__garageName__icontains=provider)
    if status:
        qs = qs.filter(isAvailable=(status == 'available'))

    # Attach template-friendly aliases
    for svc in qs:
        svc.name             = svc.serviceName
        svc.description      = svc.serviceDescription
        svc.price            = svc.servicePrice
        svc.duration_minutes = svc.estimatedDuration
        svc.is_available     = svc.isAvailable
        svc.provider         = svc.providerId   # FK object; has .garage_name below
        svc.provider.garage_name = svc.providerId.garageName

    provider_list = ServiceProvider.objects.filter(approvalStatus='approved')
    for p in provider_list:
        p.garage_name = p.garageName

    context = {
        **get_base_context(request),
        'active_section': 'services',
        'services':       qs,
        'provider_list':  provider_list,
    }
    return render(request, 'garage/Admin/services.html', context)


# ── Save / edit service ──────────────────────────────────────
@role_required(allowed_roles=["admin"])
@require_POST
def save_service(request):
    service_id  = request.POST.get('service_id', '').strip()
    name        = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    price       = request.POST.get('price', 0)
    duration    = request.POST.get('duration', 0)
    provider_name = request.POST.get('provider', '').strip()

    if not name:
        messages.warning(request, 'Service name is required.')
        return redirect('admin_services')

    if service_id:
        svc = get_object_or_404(Services, pk=service_id)
        svc.serviceName        = name
        svc.serviceDescription = description
        svc.servicePrice       = price
        svc.estimatedDuration  = duration
        svc.save()
        messages.success(request, f'"{name}" updated successfully.')
    else:
        provider_obj = ServiceProvider.objects.filter(garageName=provider_name).first()
        Services.objects.create(
            serviceName        = name,
            serviceDescription = description,
            servicePrice       = price,
            estimatedDuration  = duration,
            providerId         = provider_obj,
        )
        messages.success(request, f'"{name}" added successfully.')

    return redirect('admin_services')


# ============================================================
#  6. MONITOR BOOKINGS  —  /admin-panel/bookings/
# ============================================================
@role_required(allowed_roles=["admin"])
def monitor_bookings(request):
    q      = request.GET.get('q', '').strip()
    status = request.GET.get('status', 'all')
    bdate  = request.GET.get('date', '')
    page   = request.GET.get('page', 1)

    qs = (
        Bookings.objects
        .select_related('customer__user', 'service', 'provider')
        .order_by('-bookingDate', '-bookingTime')
    )

    if q:
        qs = qs.filter(
            Q(bookingId__icontains=q)                 |
            Q(customer__user__first_name__icontains=q)|
            Q(service__serviceName__icontains=q)      |
            Q(provider__garageName__icontains=q)
        )
    if status not in ('', 'all'):
        qs = qs.filter(bookingStatus=status)
    if bdate:
        qs = qs.filter(bookingDate=bdate)

    # Attach template-friendly aliases
    for b in qs:
        b.id         = b.bookingId
        b.status     = b.bookingStatus
        b.date       = b.bookingDate
        b.time_slot  = b.bookingTime
        b.service.name          = b.service.serviceName
        b.provider.garage_name  = b.provider.garageName
        # Amount from payment if exists
        b.amount = b.payment.amount if hasattr(b, 'payment') and b.payment else 0
        b.vehicle_number = (
            b.customer.vehicleNumber if hasattr(b.customer, 'vehicleNumber') else '—'
        )

    counts = Bookings.objects.aggregate(
        completed   = Count('bookingId', filter=Q(bookingStatus='completed')),
        in_progress = Count('bookingId', filter=Q(bookingStatus='in_progress')),
        pending     = Count('bookingId', filter=Q(bookingStatus='pending')),
        cancelled   = Count('bookingId', filter=Q(bookingStatus='cancelled')),
    )

    paginator     = Paginator(qs, 20)
    bookings_page = paginator.get_page(page)

    context = {
        **get_base_context(request),
        'active_section':   'bookings',
        'bookings':         bookings_page,
        'total_bookings':   Bookings.objects.count(),
        'completed_count':  counts['completed'],
        'inprogress_count': counts['in_progress'],
        'pending_count':    counts['pending'],
        'cancelled_count':  counts['cancelled'],
        'today_iso':        date.today().isoformat(),
    }
    return render(request, 'garage/Admin/bookings.html', context)


# ============================================================
#  7. PAYMENTS  —  /admin-panel/payments/
# ============================================================
@role_required(allowed_roles=["admin"])
def payments(request):
    q      = request.GET.get('q', '').strip()
    method = request.GET.get('method', 'all')
    status = request.GET.get('status', '')
    page   = request.GET.get('page', 1)

    qs = (
        Payments.objects
        .select_related('booking__customer__user')
        .order_by('-paymentDate')
    )

    if q:
        qs = qs.filter(
            Q(transactionId__icontains=q)                         |
            Q(booking__customer__user__first_name__icontains=q)
        )
    if method not in ('', 'all'):
        qs = qs.filter(paymentMethod=method)
    if status:
        qs = qs.filter(paymentStatus=status)

    # Template-friendly aliases
    for p in qs:
        p.id             = p.paymentId
        p.method         = p.paymentMethod
        p.status         = p.paymentStatus
        p.transaction_id = p.transactionId
        p.created_at     = p.paymentDate

    totals = Payments.objects.aggregate(
        collected      = Sum('amount', filter=Q(paymentStatus='completed')),
        pending_amount = Sum('amount', filter=Q(paymentStatus='pending')),
        failed_amount  = Sum('amount', filter=Q(paymentStatus='failed')),
        refunded_amount= Sum('amount', filter=Q(paymentStatus='refunded')),
    )

    paginator     = Paginator(qs, 20)
    payments_page = paginator.get_page(page)

    context = {
        **get_base_context(request),
        'active_section':  'payments',
        'payments':        payments_page,
        'collected':       totals['collected']       or 0,
        'pending_amount':  totals['pending_amount']  or 0,
        'failed_amount':   totals['failed_amount']   or 0,
        'refunded_amount': totals['refunded_amount'] or 0,
    }
    return render(request, 'garage/Admin/payments.html', context)


# ============================================================
#  8. INVOICES  —  /admin-panel/invoices/
# ============================================================
@role_required(allowed_roles=["admin"])
def invoices(request):
    q    = request.GET.get('q', '').strip()
    page = request.GET.get('page', 1)

    qs = (
        Invoice.objects
        .select_related('booking__customer__user')
        .order_by('-invoiceDate')
    )

    if q:
        qs = qs.filter(
            Q(invoiceNumber__icontains=q) |
            Q(booking__customer__user__first_name__icontains=q)
        )

    # Template-friendly aliases
    for inv in qs:
        inv.id             = inv.invoiceId
        inv.created_at     = inv.invoiceDate
        inv.total_amount   = inv.totalAmount
        inv.tax_amount     = inv.taxAmount
        inv.discount_amount= inv.discountAmount
        inv.service_amount = inv.totalAmount - inv.taxAmount + inv.discountAmount

    paginator     = Paginator(qs, 20)
    invoices_page = paginator.get_page(page)

    context = {
        **get_base_context(request),
        'active_section': 'invoices',
        'invoices':       invoices_page,
    }
    return render(request, 'garage/Admin/invoices.html', context)


# ── Download invoice (PDF stub — plug in WeasyPrint/ReportLab)
@role_required(allowed_roles=["admin"])
def download_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    # Stub: return a plain text receipt until PDF library is added
    content = (
        f"Invoice: {invoice.invoiceNumber}\n"
        f"Date:    {invoice.invoiceDate}\n"
        f"Total:   ₹{invoice.totalAmount}\n"
        f"Tax:     ₹{invoice.taxAmount}\n"
        f"Discount:₹{invoice.discountAmount}\n"
    )
    response = HttpResponse(content, content_type='text/plain')
    response['Content-Disposition'] = (
        f'attachment; filename="Invoice-{invoice.invoiceNumber}.txt"'
    )
    return response


# ============================================================
#  9. REVIEWS  —  /admin-panel/reviews/
# ============================================================
@role_required(allowed_roles=["admin"])
def reviews(request):
    q    = request.GET.get('q', '').strip()
    rating  = request.GET.get('rating', '')
    page = request.GET.get('page', 1)

    qs = (
        Review.objects
        .select_related('customer__user', 'provider', 'booking')
        .order_by('-createdAt')
    )

    if q:
        qs = qs.filter(
            Q(comment__icontains=q)                      |
            Q(customer__user__first_name__icontains=q)   |
            Q(provider__garageName__icontains=q)
        )
    if rating == 'low':
        qs = qs.filter(rating__lte=2)
    elif rating:
        qs = qs.filter(rating=rating)

    # Template-friendly aliases
    for r in qs:
        r.user          = r.customer.user
        r.service       = r.booking.service
        r.service.name  = r.booking.service.serviceName
        r.provider.garage_name = r.provider.garageName
        r.created_at    = r.createdAt
        r.is_flagged    = False   # Add is_flagged field to Review model if needed

    stats = Review.objects.aggregate(
        avg_rating    = Avg('rating'),
        total_reviews = Count('reviewId'),
        positive      = Count('reviewId', filter=Q(rating__gte=4)),
    )

    avg_rating    = round(stats['avg_rating'] or 0, 1)
    total_reviews = stats['total_reviews'] or 0
    positive_pct  = round((stats['positive'] / total_reviews * 100) if total_reviews else 0)

    paginator    = Paginator(qs, 20)
    reviews_page = paginator.get_page(page)

    context = {
        **get_base_context(request),
        'active_section': 'reviews',
        'reviews':        reviews_page,
        'avg_rating':     avg_rating,
        'positive_pct':   positive_pct,
        'total_reviews':  total_reviews,
        'flagged_count':  0,   # Update when is_flagged field is added
    }
    return render(request, 'garage/Admin/reviews.html', context)


# ── Flag / delete review ─────────────────────────────────────
@role_required(allowed_roles=["admin"])
def flag_review(request, pk):
    # review = get_object_or_404(Review, pk=pk)
    # review.is_flagged = True
    # review.save()
    messages.warning(request, 'Review flagged for moderation.')
    return redirect('admin_reviews')


@role_required(allowed_roles=["admin"])
def delete_review(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.delete()
    messages.success(request, 'Review deleted.')
    return redirect('admin_reviews')


# ============================================================
#  10. NOTIFICATIONS  —  /admin-panel/notifications/
# ============================================================
@role_required(allowed_roles=["admin"])
def notifications(request):
    notifs = Notification.objects.select_related('user').order_by('-createdAt')

    # Template-friendly aliases
    for n in notifs:
        n.id         = n.pk          # safe regardless of pk field name
        n.notif_type = n.notificationType
        n.is_read    = n.isRead
        n.created_at = n.createdAt
        n.recipient  = n.user

    all_users = User.objects.filter(is_active=True).order_by('first_name')

    total_sent   = Notification.objects.count()
    read_count   = Notification.objects.filter(isRead=True).count()
    unread_count = Notification.objects.filter(isRead=False).count()
    open_rate    = round((read_count / total_sent * 100) if total_sent else 0)

    context = {
        **get_base_context(request),
        'active_section':  'notifications',
        'notifications':   notifs,
        'all_users':       all_users,
        'total_sent':      total_sent,
        'read_count':      read_count,
        'unread_count':    unread_count,
        'open_rate':       open_rate,
    }
    return render(request, 'garage/Admin/notifications.html', context)


# ── Send notification ────────────────────────────────────────
@role_required(allowed_roles=["admin"])
@require_POST
def send_notification(request):
    recipient_id = request.POST.get('recipient', 'all')
    notif_type   = request.POST.get('notif_type', 'general')
    title        = request.POST.get('title', '').strip()
    message      = request.POST.get('message', '').strip()

    if not title or not message:
        messages.warning(request, 'Title and message are required.')
        return redirect('admin_notifications')

    if recipient_id == 'all':
        active_users = User.objects.filter(is_active=True)
        Notification.objects.bulk_create([
            Notification(
                user=u, title=title, message=message,
                notificationType=notif_type
            )
            for u in active_users
        ])
    else:
        user = get_object_or_404(User, pk=recipient_id)
        Notification.objects.create(
            user=user, title=title,
            message=message, notificationType=notif_type
        )

    messages.success(request, f'Notification "{title}" sent successfully.')
    return redirect('admin_notifications')


# ── Mark read ────────────────────────────────────────────────
@role_required(allowed_roles=["admin"])
def mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk)
    notif.isRead = True
    notif.save()
    # AJAX fetch (POST) → return JSON so the card fades out without reload
    if request.method == 'POST':
        return JsonResponse({'success': True})
    messages.success(request, 'Notification marked as read.')
    return redirect('admin_notifications')


@role_required(allowed_roles=["admin"])
def mark_all_read(request):
    Notification.objects.filter(isRead=False).update(isRead=True)
    messages.success(request, 'All notifications marked as read.')
    return redirect('admin_notifications')


# ============================================================
#  11. DISPUTES  —  /admin-panel/disputes/
#  NOTE: No Dispute model in models.py yet.
#        Add it and uncomment the queryset below.
# ============================================================
@role_required(allowed_roles=["admin"])
def disputes(request):
    # status = request.GET.get('status', 'all')
    # qs = Dispute.objects.select_related('customer', 'provider', 'booking').order_by('-created_at')
    # if status not in ('', 'all'):
    #     qs = qs.filter(status=status)
    qs = []

    context = {
        **get_base_context(request),
        'active_section': 'disputes',
        'disputes':       qs,
        'open_count':     0,
        'review_count':   0,
        'resolved_count': 0,
        'closed_count':   0,
    }
    return render(request, 'garage/Admin/disputes.html', context)


@role_required(allowed_roles=["admin"])
def resolve_dispute(request, pk):
    # dispute = get_object_or_404(Dispute, pk=pk)
    # dispute.status = 'resolved'
    # dispute.save()
    messages.success(request, f'Dispute #{pk} marked as resolved.')
    return redirect('admin_disputes')


# ============================================================
#  12. ANALYTICS  —  /admin-panel/analytics/
# ============================================================
@role_required(allowed_roles=["admin"])
def analytics(request):
    today = date.today()

    # ── KPI cards ──────────────────────────────────────────
    page_views    = User.objects.count() * 15          # estimate
    # new_signups   = User.objects.filter(
    #     date_joined__month=today.month,
    #     date_joined__year=today.year
    # ).count()
    new_signups = User.objects.filter(
    created_at__month=today.month,
    created_at__year=today.year
    ).count()
    avg_rating_val = Review.objects.aggregate(a=Avg('rating'))['a'] or 0
    avg_rating     = round(avg_rating_val, 1)

    total_bookings = Bookings.objects.count()
    completed      = Bookings.objects.filter(bookingStatus='completed').count()
    conversion_rate = round((completed / total_bookings * 100) if total_bookings else 0)

    # ── Horizontal bar: top 6 services by booking count ────
    COLORS = ['#e8560a', '#1e3a5f', '#f9a825', '#16a34a', '#7c3aed', '#dc2626']
    service_qs = (
        Bookings.objects
        .values('service__serviceName')
        .annotate(count=Count('bookingId'))
        .order_by('-count')[:6]
    )
    max_count = service_qs[0]['count'] if service_qs else 1
    service_stats = [
        {
            'name':  item['service__serviceName'],
            'count': item['count'],
            'pct':   round(item['count'] / max_count * 100),
            'color': COLORS[i % 6],
        }
        for i, item in enumerate(service_qs)
    ]

    # ── Vertical bar: new user registrations last 6 months ─
    six_months_ago = today.replace(day=1) - timedelta(days=150)
    growth_qs = (
        User.objects
        .filter(created_at__gte=six_months_ago)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    max_growth = max((g['count'] for g in growth_qs), default=1)
    monthly_signups = [
        {
            'month': month_abbr[g['month'].month],
            'count': g['count'],
            'pct':   round(g['count'] / max_growth * 100),
        }
        for g in growth_qs
    ]

    context = {
        **get_base_context(request),
        'active_section':   'analytics',
        'page_views':       page_views,
        'new_signups':      new_signups,
        'conversion_rate':  conversion_rate,
        'avg_rating':       avg_rating,
        'service_stats':    service_stats,
        'monthly_signups':  monthly_signups,
    }
    return render(request, 'garage/Admin/analytics.html', context)


# ============================================================
#  13. GENERATE REPORTS  —  /admin-panel/reports/
# ============================================================
@role_required(allowed_roles=["admin"])
def generate_reports(request):
    context = {
        **get_base_context(request),
        'active_section': 'reports',
    }
    return render(request, 'garage/Admin/reports.html', context)


# ── Export CSV / PDF / Excel ─────────────────────────────────
@role_required(allowed_roles=["admin"])
def export_report(request, report_type, fmt):

    # Safe name — uses first_name+last_name fields directly, never get_full_name()
    # Avoids AttributeError on custom User models + avoids any recursion risk
    def _uname(u):
        fn = (getattr(u, 'first_name', '') or '').strip()
        ln = (getattr(u, 'last_name',  '') or '').strip()
        name = (fn + ' ' + ln).strip()
        return name if name else (getattr(u, 'username', '') or getattr(u, 'email', '') or 'Unknown')

    period       = request.GET.get('period', 'month')
    extra        = request.GET.get('extra', '')
    today        = date.today()
    period_label = {'last_month': 'Last Month', 'year': 'This Year'}.get(period, 'This Month')
    fname        = report_type + '_report_' + str(today)

    if period == 'last_month':
        first_day = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_day  = today.replace(day=1) - timedelta(days=1)
    elif period == 'year':
        first_day = today.replace(month=1, day=1)
        last_day  = today
    else:
        first_day = today.replace(day=1)
        last_day  = today

    # ── BOOKINGS ─────────────────────────────────────────────
    if report_type == 'bookings':
        qs = Bookings.objects.filter(
            bookingDate__range=(first_day, last_day)
        ).select_related('customer__user', 'service', 'provider').order_by('-bookingDate')
        if extra:
            qs = qs.filter(bookingStatus=extra)
        headers = ['ID', 'Customer', 'Email', 'Service', 'Provider', 'Date', 'Status', 'Notes']
        rows = []
        for b in qs:
            rows.append([
                'BK' + str(b.bookingId),
                _uname(b.customer.user),
                b.customer.user.email,
                b.service.serviceName,
                b.provider.garageName,
                str(b.bookingDate),
                b.bookingStatus.replace('_', ' ').title(),
                b.notes or '',
            ])
        title = 'Bookings Report - ' + period_label

    # ── PAYMENTS ─────────────────────────────────────────────
    elif report_type == 'payments':
        qs = Payments.objects.filter(
            paymentDate__date__range=(first_day, last_day)
        ).select_related('booking__customer__user', 'booking__service').order_by('-paymentDate')
        if extra:
            qs = qs.filter(paymentMethod=extra.lower())
        headers = ['ID', 'Customer', 'Service', 'Amount', 'Method', 'Status', 'Txn ID', 'Date']
        rows = []
        for p in qs:
            rows.append([
                'PAY' + str(p.paymentId),
                _uname(p.booking.customer.user),
                p.booking.service.serviceName,
                str(p.amount),
                p.paymentMethod.title(),
                p.paymentStatus.title(),
                p.transactionId or '',
                str(p.paymentDate.date()),
            ])
        title = 'Payments Report - ' + period_label

    # ── SERVICE PROVIDERS ────────────────────────────────────
    elif report_type == 'providers':
        qs = ServiceProvider.objects.select_related('user').order_by('garageName')
        if extra:
            qs = qs.filter(approvalStatus=extra.lower())
        headers = ['ID', 'Garage Name', 'Owner', 'Email', 'Location', 'Rating', 'Status', 'Opening', 'Closing']
        rows = []
        for p in qs:
            rows.append([
                str(p.providerId),
                p.garageName,
                _uname(p.user),
                p.user.email,
                p.location,
                str(p.rating),
                p.approvalStatus.title(),
                str(p.openingTime),
                str(p.closingTime),
            ])
        title = 'Service Providers Report - ' + period_label

    # ── USERS ────────────────────────────────────────────────
    elif report_type == 'users':
        try:
            qs = User.objects.filter(
                created_at__date__gte=first_day,
                created_at__date__lte=last_day,
            ).order_by('-created_at')
        except Exception:
            qs = User.objects.all().order_by('pk')
        if extra:
            try:
                qs = qs.filter(role=extra.lower())
            except Exception:
                pass
        headers = ['ID', 'Full Name', 'Email', 'Role', 'Joined', 'Active']
        rows = []
        for u in qs:
            try:
                joined = str(u.created_at.date())
            except Exception:
                joined = ''
            rows.append([
                str(u.pk),
                _uname(u),
                getattr(u, 'email', ''),
                getattr(u, 'role', '').replace('_', ' ').title(),
                joined,
                'Yes' if u.is_active else 'No',
            ])
        title = 'Users Report - ' + period_label

    # ── INVOICES ─────────────────────────────────────────────
    elif report_type == 'invoices':
        qs = Invoice.objects.filter(
            invoiceDate__range=(first_day, last_day)
        ).select_related('booking__customer__user', 'booking__service',
                         'booking__provider').order_by('-invoiceDate')
        headers = ['Invoice No', 'Customer', 'Service', 'Provider', 'Date', 'Total', 'Tax', 'Discount']
        rows = []
        for inv in qs:
            rows.append([
                inv.invoiceNumber,
                _uname(inv.booking.customer.user),
                inv.booking.service.serviceName,
                inv.booking.provider.garageName,
                str(inv.invoiceDate),
                str(inv.totalAmount),
                str(inv.taxAmount),
                str(inv.discountAmount),
            ])
        title = 'Invoices Report - ' + period_label

    # ── REVIEWS ──────────────────────────────────────────────
    elif report_type == 'reviews':
        qs = Review.objects.filter(
            createdAt__date__range=(first_day, last_day)
        ).select_related('customer__user', 'provider').order_by('-createdAt')
        if extra == '5':     qs = qs.filter(rating=5)
        elif extra == '4':   qs = qs.filter(rating=4)
        elif extra == 'low': qs = qs.filter(rating__lte=2)
        headers = ['ID', 'Customer', 'Provider', 'Rating', 'Comment', 'Date']
        rows = []
        for rv in qs:
            rows.append([
                str(rv.reviewId),
                _uname(rv.customer.user),
                rv.provider.garageName,
                str(rv.rating) + '/5',
                rv.comment or '',
                str(rv.createdAt.date()),
            ])
        title = 'Reviews Report - ' + period_label

    else:
        messages.warning(request, 'Unknown report type.')
        return redirect('admin_reports')

    # ════════════════════════════════════════════════
    #  CSV
    # ════════════════════════════════════════════════
    if fmt == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="' + fname + '.csv"'
        response.write('﻿')
        w = csv.writer(response)
        w.writerow([title])
        w.writerow(['Generated: ' + str(today) + '  |  Records: ' + str(len(rows))])
        w.writerow([])
        w.writerow(headers)
        w.writerows(rows)
        return response

    # ════════════════════════════════════════════════
    #  EXCEL (pip install openpyxl)
    # ════════════════════════════════════════════════
    elif fmt == 'excel':
        try:
            import io as _io
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
            from openpyxl.cell.cell import MergedCell
        except ImportError:
            messages.error(
                request,
                'Excel export requires openpyxl. '
                'Run: pip install openpyxl  inside your virtualenv then restart the server.'
            )
            return redirect('admin_reports')

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = report_type.title()

        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
        tc = ws.cell(row=1, column=1, value=title)
        tc.font      = Font(bold=True, size=13, color='FFFFFF')
        tc.fill      = PatternFill('solid', fgColor='E8560A')
        tc.alignment = Alignment(horizontal='center')

        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(headers))
        sc = ws.cell(row=2, column=1, value='Generated: ' + str(today) + '   |   Records: ' + str(len(rows)))
        sc.font      = Font(size=10, color='555555')
        sc.alignment = Alignment(horizontal='center')

        ws.append([])

        hfill = PatternFill('solid', fgColor='1E3A5F')
        for ci, h in enumerate(headers, 1):
            c = ws.cell(row=4, column=ci, value=h)
            c.font      = Font(bold=True, color='FFFFFF', size=10)
            c.fill      = hfill
            c.alignment = Alignment(horizontal='center')

        for ri, row in enumerate(rows, 5):
            bg = PatternFill('solid', fgColor='F2F2F2') if ri % 2 == 0 else None
            for ci, val in enumerate(row, 1):
                c = ws.cell(row=ri, column=ci, value=str(val))
                c.alignment = Alignment(horizontal='left')
                if bg:
                    c.fill = bg

        for col in ws.columns:
            max_w      = 8
            col_letter = None
            for cell in col:
                if isinstance(cell, MergedCell):
                    continue
                if col_letter is None:
                    col_letter = cell.column_letter
                if len(str(cell.value or '')) > max_w:
                    max_w = len(str(cell.value or ''))
            if col_letter:
                ws.column_dimensions[col_letter].width = min(max_w + 4, 45)

        buf = _io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        resp = HttpResponse(
            buf.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        resp['Content-Disposition'] = 'attachment; filename="' + fname + '.xlsx"'
        return resp

    # ════════════════════════════════════════════════
    #  PDF (pure HTML, zero dependencies)
    # ════════════════════════════════════════════════
    elif fmt == 'pdf':
        th_cells  = ''.join('<th>' + str(h) + '</th>' for h in headers)
        body_rows = ''
        for i, row in enumerate(rows):
            cls = 'alt' if i % 2 == 0 else ''
            tds = ''.join('<td>' + str(v) + '</td>' for v in row)
            body_rows += '<tr class="' + cls + '">' + tds + '</tr>'
        html = (
            '<!DOCTYPE html><html><head><meta charset="utf-8">'
            '<title>' + title + '</title>'
            '<style>'
            '@page{size:A4 landscape;margin:12mm}'
            '*{box-sizing:border-box;margin:0;padding:0;font-family:Arial,sans-serif}'
            'body{padding:16px;color:#111}'
            '.hdr{display:flex;justify-content:space-between;align-items:flex-end;'
            'border-bottom:3px solid #e8560a;padding-bottom:10px;margin-bottom:14px}'
            '.brand{font-size:20px;font-weight:700;color:#e8560a}'
            '.brand span{color:#1e3a5f}'
            '.meta{font-size:11px;color:#555;text-align:right}'
            'h2{font-size:15px;font-weight:700;color:#1e3a5f;margin-bottom:2px}'
            'table{width:100%;border-collapse:collapse;font-size:10px}'
            'thead tr{background:#1e3a5f;color:#fff}'
            'thead th{padding:6px 7px;text-align:left;font-weight:600}'
            'tbody td{padding:5px 7px;border-bottom:1px solid #e5e7eb}'
            'tr.alt td{background:#f5f5f5}'
            '.foot{margin-top:12px;font-size:9px;color:#aaa;text-align:center}'
            '.pbtn{display:inline-block;margin-bottom:14px;padding:9px 20px;'
            'background:#e8560a;color:#fff;border:none;border-radius:6px;'
            'font-size:13px;font-weight:700;cursor:pointer}'
            '@media print{.pbtn{display:none}}'
            '</style></head><body>'
            '<button class="pbtn" onclick="window.print()">Print / Save as PDF</button>'
            '<div class="hdr"><div><div class="brand">e<span>Garage</span></div>'
            '<h2>' + title + '</h2></div>'
            '<div class="meta">Generated: ' + str(today) + '<br>'
            'Records: ' + str(len(rows)) + '<br>Period: ' + period_label + '</div></div>'
            '<table><thead><tr>' + th_cells + '</tr></thead>'
            '<tbody>' + body_rows + '</tbody></table>'
            '<div class="foot">eGarage Admin Portal - ' + str(today) + '</div>'
            '<script>setTimeout(function(){window.print();},500);</script>'
            '</body></html>'
        )
        return HttpResponse(html, content_type='text/html; charset=utf-8')

    messages.warning(request, 'Unknown format: ' + str(fmt))
    return redirect('admin_reports')


# ============================================================
#  GENERIC DELETE
# ============================================================
@role_required(allowed_roles=["admin"])
def generic_delete(request):
    model_type  = request.POST.get('model_type', '') or request.GET.get('model_type', '')
    object_id   = request.POST.get('object_id', '') or request.GET.get('object_id', '')
    redirect_to = request.POST.get('redirect_to', '') or request.GET.get('redirect_to', 'admin_overview')

    model_map = {
        'user':     User,
        'provider': ServiceProvider,
        'service':  Services,
        'booking':  Bookings,
        'review':   Review,
    }
    Model = model_map.get(model_type)
    if Model and object_id:
        obj = get_object_or_404(Model, pk=object_id)
        obj.delete()
        messages.success(request, f'{model_type.title()} deleted successfully.')
    else:
        messages.warning(request, 'Could not delete: unknown type or missing ID.')

    return redirect(redirect_to)


# ============================================================
#  LOGOUT
# ============================================================
def admin_logout(request):
    logout(request)
    return redirect('login')





# ============================================================
#  SHARED CUSTOMER CONTEXT  (sidebar live counts)
# ============================================================
def get_customer_context(request):
    """
    Returns sidebar badge counts for the logged-in customer.
    """
    customer = getattr(request.user, 'customer_profile', None)
    pending_bookings = 0
    upcoming_bookings = 0
    unread_notifs = 0
 
    if customer:
        pending_bookings = Bookings.objects.filter(
            customer=customer,
            bookingStatus__in=['pending', 'confirmed']
        ).count()
        upcoming_bookings = Bookings.objects.filter(
            customer=customer,
            bookingDate__gte=date.today(),
            bookingStatus__in=['pending', 'confirmed']
        ).count()
 
    unread_notifs = Notification.objects.filter(
        user=request.user,
        isRead=False
    ).count()
 
    return {
        'customer_profile':    customer,
        'pending_count':       pending_bookings,
        'upcoming_count':      upcoming_bookings,
        'unread_notif_count':  unread_notifs,
    }
 
 
# ============================================================
#  REDIRECT  /customer/  → home
# ============================================================
# @role_required(allowed_roles=["customer"])
# def customerdashboard(request):
#     return redirect('customer_home')
 
 
# ============================================================
#  1. HOME / OVERVIEW  —  /customer/home/
# ============================================================
@role_required(allowed_roles=["customer"])
def customer_home(request):
    customer = get_object_or_404(CustomerProfile, user=request.user)
 
    # ── Stat cards ─────────────────────────────────────────
    total_bookings     = Bookings.objects.filter(customer=customer).count()
    completed_bookings = Bookings.objects.filter(
        customer=customer, bookingStatus='completed'
    ).count()
    upcoming_bookings  = Bookings.objects.filter(
        customer=customer,
        bookingDate__gte=date.today(),
        bookingStatus__in=['pending', 'confirmed']
    ).count()
    total_spent = (
        Payments.objects
        .filter(booking__customer=customer, paymentStatus='completed')
        .aggregate(total=Sum('amount'))['total'] or 0
    )
 
    # ── Recent 4 bookings ──────────────────────────────────
    recent_bookings = (
        Bookings.objects
        .filter(customer=customer)
        .select_related('service', 'provider')
        .order_by('-bookingDate', '-createdAt')[:4]
    )
 
    context = {
        **get_customer_context(request),
        'active': 'home',
 
        # stat cards
        'total_bookings':     total_bookings,
        'completed_bookings': completed_bookings,
        'upcoming_bookings':  upcoming_bookings,
        'total_spent':        total_spent,
 
        # recent bookings table
        'recent_bookings':    recent_bookings,
    }
    return render(request, 'garage/Customer/home.html', context)
 
 
# ============================================================
#  2. BOOK SERVICE  —  /customer/book/
# ============================================================
@role_required(allowed_roles=["customer"])
def book_service(request):
    """
    GET  → Show available services + booking form.
    POST → Create a new Booking record.
    """
    if request.method == 'POST':
        customer    = get_object_or_404(CustomerProfile, user=request.user)
        service_id  = request.POST.get('service_id')
        provider_id = request.POST.get('provider_id')
        bdate       = request.POST.get('booking_date')
        btime       = request.POST.get('booking_time') or None
        notes       = request.POST.get('notes', '').strip()
 
        if not service_id or not bdate:
            messages.error(request, 'Please select a service and booking date.')
            return redirect('book_service')
 
        service  = get_object_or_404(Services, pk=service_id, isAvailable=True)
        provider = get_object_or_404(ServiceProvider, pk=provider_id, approvalStatus='approved')
 
        Bookings.objects.create(
            customer      = customer,
            provider      = provider,
            service       = service,
            bookingDate   = bdate,
            bookingTime   = btime,
            notes         = notes,
            bookingStatus = 'pending',
        )
 
        # Send a confirmation notification to the customer
        Notification.objects.create(
            user             = request.user,
            notificationType = 'booking_confirmed',
            title            = 'Booking Request Received',
            message          = (
                f'Your booking for {service.serviceName} at '
                f'{provider.garageName} on {bdate} has been received '
                f'and is pending confirmation.'
            ),
        )
 
        messages.success(request, 'Booking confirmed! Check My Bookings for status.')
        return redirect('my_bookings')
 
    # ── GET: show all available services ─────────────────
    all_services  = (
        Services.objects
        .filter(isAvailable=True)
        .select_related('providerId')
        .order_by('serviceName')
    )
    all_providers = ServiceProvider.objects.filter(approvalStatus='approved')
 
    context = {
        **get_customer_context(request),
        'active':       'book',
        'services':     all_services,
        'providers':    all_providers,
        'today_iso':    date.today().isoformat(),
    }
    return render(request, 'garage/Customer/book_service.html', context)
 
 
# ============================================================
#  3. MY BOOKINGS  —  /customer/bookings/
# ============================================================
@role_required(allowed_roles=["customer"])
def my_bookings(request):
    customer = get_object_or_404(CustomerProfile, user=request.user)
    status   = request.GET.get('status', 'all')
    page     = request.GET.get('page', 1)
 
    qs = (
        Bookings.objects
        .filter(customer=customer)
        .select_related('service', 'provider')
        .order_by('-bookingDate', '-createdAt')
    )
 
    if status not in ('', 'all'):
        qs = qs.filter(bookingStatus=status)
 
    paginator     = Paginator(qs, 10)
    bookings_page = paginator.get_page(page)
 
    context = {
        **get_customer_context(request),
        'active':    'bookings',
        'bookings':  bookings_page,
        'status':    status,
    }
    return render(request, 'garage/Customer/my_bookings.html', context)
 
 
# ── Cancel a booking ─────────────────────────────────────────
@role_required(allowed_roles=["customer"])
@require_POST
def cancel_booking(request, pk):
    customer = get_object_or_404(CustomerProfile, user=request.user)
    booking  = get_object_or_404(Bookings, pk=pk, customer=customer)
 
    if booking.bookingStatus in ('pending', 'confirmed'):
        booking.bookingStatus = 'cancelled'
        booking.save()
        # Notify customer of cancellation
        Notification.objects.create(
            user             = request.user,
            notificationType = 'booking_cancelled',
            title            = 'Booking Cancelled',
            message          = (
                f'Your booking #{booking.bookingId} for '
                f'{booking.service.serviceName} has been cancelled.'
            ),
        )
        messages.success(request, f'Booking #{booking.bookingId} cancelled successfully.')
    else:
        messages.error(request, 'This booking cannot be cancelled.')
 
    return redirect('my_bookings')
 
 
# ============================================================
#  4. SERVICE HISTORY  —  /customer/history/
# ============================================================
@role_required(allowed_roles=["customer"])
def service_history(request):
    customer = get_object_or_404(CustomerProfile, user=request.user)
 
    completed = (
        Bookings.objects
        .filter(customer=customer, bookingStatus='completed')
        .select_related('service', 'provider')
        .prefetch_related('review', 'invoice')
        .order_by('-bookingDate')
    )
 
    # Attach invoice and review to each booking for the template
    history = []
    for b in completed:
        invoice = getattr(b, 'invoice', None)
        review  = getattr(b, 'review', None)
        history.append({
            'booking': b,
            'invoice': invoice,
            'review':  review,
            'amount':  invoice.totalAmount if invoice else (
                b.payment.amount if hasattr(b, 'payment') and b.payment else 0
            ),
        })
 
    context = {
        **get_customer_context(request),
        'active':  'history',
        'history': history,
    }
    return render(request, 'garage/Customer/service_history.html', context)
 
 
# ── Download invoice ──────────────────────────────────────────
@role_required(allowed_roles=["customer"])
def customer_download_invoice(request, pk):
    customer = get_object_or_404(CustomerProfile, user=request.user)
    invoice  = get_object_or_404(Invoice, pk=pk, booking__customer=customer)
 
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="invoice_{invoice.invoiceNumber}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(['E-Garage Invoice'])
    writer.writerow([])
    writer.writerow(['Invoice No.',    invoice.invoiceNumber])
    writer.writerow(['Date',           invoice.invoiceDate])
    writer.writerow(['Customer',       request.user.get_full_name()])
    writer.writerow(['Service',        invoice.booking.service.serviceName])
    writer.writerow(['Provider',       invoice.booking.provider.garageName])
    writer.writerow([])
    writer.writerow(['Service Amount', invoice.totalAmount - invoice.taxAmount + invoice.discountAmount])
    writer.writerow(['Tax',            invoice.taxAmount])
    writer.writerow(['Discount',       invoice.discountAmount])
    writer.writerow(['Total Amount',   invoice.totalAmount])
    return response
 
 
# ── Submit a review ───────────────────────────────────────────
@role_required(allowed_roles=["customer"])
@require_POST
def submit_review(request, booking_pk):
    customer = get_object_or_404(CustomerProfile, user=request.user)
    booking  = get_object_or_404(
        Bookings, pk=booking_pk, customer=customer, bookingStatus='completed'
    )
 
    # Prevent duplicate reviews
    if hasattr(booking, 'review'):
        messages.warning(request, 'You have already reviewed this booking.')
        return redirect('service_history')
 
    rating  = request.POST.get('rating', 5)
    comment = request.POST.get('comment', '').strip()
 
    Review.objects.create(
        booking  = booking,
        customer = customer,
        provider = booking.provider,
        rating   = int(rating),
        comment  = comment,
    )
 
    # Update the provider's average rating
    avg = Review.objects.filter(
        provider=booking.provider
    ).aggregate(avg=Avg('rating'))['avg'] or 0
    booking.provider.rating = round(avg, 1)
    booking.provider.save()
 
    messages.success(request, 'Thank you for your review!')
    return redirect('service_history')
 
 
# ============================================================
#  5. MY VEHICLE  —  /customer/vehicle/
# ============================================================
@role_required(allowed_roles=["customer"])
def my_vehicle(request):
    """
    GET  → Show current vehicle details with edit form.
    POST → Update or create CustomerProfile with new vehicle info.
    """
    customer = CustomerProfile.objects.filter(user=request.user).first()
 
    if request.method == 'POST':
        vehicle_type   = request.POST.get('vehicle_type', 'car')
        vehicle_number = request.POST.get('vehicle_number', '').strip().upper()
        vehicle_model  = request.POST.get('vehicle_model', '').strip()
        vehicle_year   = request.POST.get('vehicle_year') or None
        vehicle_color  = request.POST.get('vehicle_color', '').strip()
 
        if not vehicle_number or not vehicle_model:
            messages.error(request, 'Vehicle number and model are required.')
            return redirect('my_vehicle')
 
        if customer:
            # Update existing profile
            customer.vehicleType   = vehicle_type
            customer.vehicleNumber = vehicle_number
            customer.vehicleModel  = vehicle_model
            customer.vehicleYear   = vehicle_year
            customer.vehicleColor  = vehicle_color
            customer.save()
        else:
            # Create new customer profile
            customer = CustomerProfile.objects.create(
                user          = request.user,
                vehicleType   = vehicle_type,
                vehicleNumber = vehicle_number,
                vehicleModel  = vehicle_model,
                vehicleYear   = vehicle_year,
                vehicleColor  = vehicle_color,
            )
 
        messages.success(request, 'Vehicle details updated successfully!')
        return redirect('my_vehicle')
 
    # Count services done on this vehicle
    services_done = 0
    last_service  = None
    if customer:
        services_done = Bookings.objects.filter(
            customer=customer, bookingStatus='completed'
        ).count()
        last_bk = (
            Bookings.objects
            .filter(customer=customer, bookingStatus='completed')
            .order_by('-bookingDate')
            .first()
        )
        if last_bk:
            last_service = last_bk.bookingDate
 
    context = {
        **get_customer_context(request),
        'active':        'vehicle',
        'customer':      customer,
        'services_done': services_done,
        'last_service':  last_service,
    }
    return render(request, 'garage/Customer/my_vehicle.html', context)
 
 
# ============================================================
#  6. PAYMENTS  —  /customer/payments/
# ============================================================
@role_required(allowed_roles=["customer"])
def my_payments(request):
    customer = get_object_or_404(CustomerProfile, user=request.user)
 
    qs = (
        Payments.objects
        .filter(booking__customer=customer)
        .select_related('booking__service', 'booking__provider')
        .order_by('-paymentDate')
    )
 
    # ── Payment summary stats ──────────────────────────────
    totals = qs.aggregate(
        total_paid    = Sum('amount', filter=Q(paymentStatus='completed')),
        total_pending = Sum('amount', filter=Q(paymentStatus='pending')),
        total_refund  = Sum('amount', filter=Q(paymentStatus='refunded')),
    )
 
    paginator    = Paginator(qs, 10)
    payment_page = paginator.get_page(request.GET.get('page', 1))
 
    context = {
        **get_customer_context(request),
        'active':         'payments',
        'payments':       payment_page,
        'total_paid':     totals['total_paid']    or 0,
        'total_pending':  totals['total_pending'] or 0,
        'total_refund':   totals['total_refund']  or 0,
    }
    return render(request, 'garage/Customer/my_payments.html', context)
 
 
# ============================================================
#  7. NOTIFICATIONS  —  /customer/notifications/
# ============================================================
@role_required(allowed_roles=["customer"])
def customer_notifications(request):
    notifs = (
        Notification.objects
        .filter(user=request.user)
        .order_by('-createdAt')
    )
 
    # Stats
    total_sent  = notifs.count()
    total_read  = notifs.filter(isRead=True).count()
    total_unread = notifs.filter(isRead=False).count()
 
    paginator   = Paginator(notifs, 15)
    notif_page  = paginator.get_page(request.GET.get('page', 1))
 
    context = {
        **get_customer_context(request),
        'active':        'notifications',
        'notifications': notif_page,
        'total_sent':    total_sent,
        'total_read':    total_read,
        'total_unread':  total_unread,
    }
    return render(request, 'garage/Customer/notifications.html', context)
 
 
# ── Mark single notification as read ─────────────────────────
@role_required(allowed_roles=["customer"])
def mark_notif_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.isRead = True
    notif.save()
    return redirect('customer_notifications')
 
 
# ── Mark all notifications as read ───────────────────────────
@role_required(allowed_roles=["customer"])
def mark_all_notif_read(request):
    Notification.objects.filter(user=request.user, isRead=False).update(isRead=True)
    messages.success(request, 'All notifications marked as read.')
    return redirect('customer_notifications')
 
 
# ============================================================
#  8. MY PROFILE  —  /customer/profile/
# ============================================================
@role_required(allowed_roles=["customer"])
def customer_profile(request):
    if request.method == 'POST':
        action = request.POST.get('action', 'profile')
 
        if action == 'profile':
            # Update personal info
            user           = request.user
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name  = request.POST.get('last_name', '').strip()
            user.mobile     = request.POST.get('mobile', '').strip()
            user.gender     = request.POST.get('gender', '').strip()
            user.save()
            messages.success(request, 'Profile updated successfully!')
 
        elif action == 'password':
            # Change password
            current_pw  = request.POST.get('current_password', '')
            new_pw      = request.POST.get('new_password', '')
            confirm_pw  = request.POST.get('confirm_password', '')
 
            if not request.user.check_password(current_pw):
                messages.error(request, 'Current password is incorrect.')
            elif new_pw != confirm_pw:
                messages.error(request, 'New passwords do not match.')
            elif len(new_pw) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
            else:
                request.user.set_password(new_pw)
                request.user.save()
                messages.success(
                    request,
                    'Password changed! Please log in again.'
                )
                return redirect('login')
 
        return redirect('customer_profile')
 
    # ── GET ──────────────────────────────────────────────
    customer = CustomerProfile.objects.filter(user=request.user).first()
 
    # Account summary stats
    total_bookings = 0
    member_since   = getattr(request.user, 'created_at', request.user.date_joined)
    if customer:
        total_bookings = Bookings.objects.filter(customer=customer).count()
 
    context = {
        **get_customer_context(request),
        'active':          'profile',
        'customer':        customer,
        'total_bookings':  total_bookings,
        'member_since':    member_since,
    }
    return render(request, 'garage/Customer/profile.html', context)
 
 
# ============================================================
#  CUSTOMER LOGOUT
# ============================================================
 
def customer_logout(request):
    auth_logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')






# @role_required(allowed_roles=["service_provider"])
# def serviceProviderdashboard(request):
#     return render(request, "garage/Admin/ServiceProvider/serviceprovider_dashboard.html")


# ============================================================
#  SHARED PROVIDER CONTEXT  (sidebar live counts)
# ============================================================
def get_provider_context(request):
    provider = ServiceProvider.objects.filter(user=request.user).first()
    pending_count   = 0
    unread_count    = 0
    total_reviews   = 0
 
    if provider:
        pending_count = Bookings.objects.filter(
            provider=provider, bookingStatus='pending'
        ).count()
        total_reviews = Review.objects.filter(provider=provider).count()
 
    unread_count = Notification.objects.filter(
        user=request.user, isRead=False
    ).count()
 
    return {
        'provider':              provider,
        'pending_bookings_count': pending_count,
        'unread_notif_count':    unread_count,
        'total_reviews':         total_reviews,
    }
 
 
# ============================================================
#  REDIRECT  /serviceProvider/  →  overview
# ============================================================
@role_required(allowed_roles=["service_provider"])
def serviceProviderdashboard(request):
    return redirect('provider_overview')
 
 
# ============================================================
#  1. OVERVIEW  —  /serviceProvider/overview/
# ============================================================
@role_required(allowed_roles=["service_provider"])
def provider_overview(request):
    provider = ServiceProvider.objects.filter(user=request.user).first()
    if not provider:
        messages.warning(request, 'Your provider profile is not set up yet.')
        return redirect('provider_profile')
 
    today = date.today()
 
    total_bookings  = Bookings.objects.filter(provider=provider).count()
    pending_count   = Bookings.objects.filter(provider=provider, bookingStatus='pending').count()
    monthly_revenue = (
        Payments.objects
        .filter(booking__provider=provider, paymentStatus='completed',
                paymentDate__month=today.month, paymentDate__year=today.year)
        .aggregate(total=Sum('amount'))['total'] or 0
    )
    monthly_count = Bookings.objects.filter(
        provider=provider,
        bookingDate__month=today.month,
        bookingDate__year=today.year
    ).count()
 
    # Completion rate
    completed = Bookings.objects.filter(provider=provider, bookingStatus='completed').count()
    completion_rate = round((completed / total_bookings * 100) if total_bookings else 0)
 
    # Avg duration from services
    avg_duration = round(
        Services.objects.filter(providerId=provider)
        .aggregate(avg=AvgF('estimatedDuration'))['avg'] or 0
    )
    services_count = Services.objects.filter(providerId=provider, isAvailable=True).count()
 
    # Monthly booking trend (last 7 months)
    six_months_ago = (today.replace(day=1) - timedelta(days=180))
    monthly_qs = (
        Bookings.objects
        .filter(provider=provider, bookingDate__gte=six_months_ago)
        .annotate(month=TruncMonth('bookingDate'))
        .values('month')
        .annotate(count=Count('bookingId'))
        .order_by('month')
    )
    max_count = max((m['count'] for m in monthly_qs), default=1)
    monthly_bookings = [
        {
            'month': month_abbr[m['month'].month],
            'count': m['count'],
            'pct':   round(m['count'] / max_count * 100),
        }
        for m in monthly_qs
    ]
 
    # Today's bookings
    todays_bookings = (
        Bookings.objects
        .filter(provider=provider, bookingDate=today)
        .select_related('customer__user', 'service')
        .order_by('bookingTime')
    )
 
    context = {
        **get_provider_context(request),
        'active':           'overview',
        'today':            today.strftime('%d %b %Y'),
        'total_bookings':   total_bookings,
        'pending_count':    pending_count,
        'monthly_revenue':  monthly_revenue,
        'monthly_count':    monthly_count,
        'completion_rate':  completion_rate,
        'avg_duration':     avg_duration,
        'services_count':   services_count,
        'monthly_bookings': monthly_bookings,
        'todays_bookings':  todays_bookings,
    }
    return render(request, 'garage/Provider/overview.html', context)
 
 
# ============================================================
#  2. BOOKINGS  —  /serviceProvider/bookings/
# ============================================================
@role_required(allowed_roles=["service_provider"])
def provider_bookings(request):
    provider = get_object_or_404(ServiceProvider, user=request.user)
    status   = request.GET.get('status', 'all')
    page     = request.GET.get('page', 1)
 
    qs = (
        Bookings.objects
        .filter(provider=provider)
        .select_related('customer__user', 'service')
        .order_by('-bookingDate', '-bookingTime')
    )
    if status not in ('', 'all'):
        qs = qs.filter(bookingStatus=status)
 
    counts = Bookings.objects.filter(provider=provider).aggregate(
        pending    = Count('bookingId', filter=Q(bookingStatus='pending')),
        inprogress = Count('bookingId', filter=Q(bookingStatus='in_progress')),
        completed  = Count('bookingId', filter=Q(bookingStatus='completed')),
        cancelled  = Count('bookingId', filter=Q(bookingStatus='cancelled')),
    )
 
    paginator     = Paginator(qs, 12)
    bookings_page = paginator.get_page(page)
 
    context = {
        **get_provider_context(request),
        'active':           'bookings',
        'bookings':         bookings_page,
        'status':           status,
        'pending_count':    counts['pending'],
        'inprogress_count': counts['inprogress'],
        'completed_count':  counts['completed'],
        'cancelled_count':  counts['cancelled'],
    }
    return render(request, 'garage/Provider/bookings.html', context)
 
 
# ── Booking detail ────────────────────────────────────────────
@role_required(allowed_roles=["service_provider"])
def provider_booking_detail(request, pk):
    provider = get_object_or_404(ServiceProvider, user=request.user)
    booking  = get_object_or_404(Bookings, pk=pk, provider=provider)
    context  = {
        **get_provider_context(request),
        'active':  'bookings',
        'booking': booking,
    }
    return render(request, 'garage/Provider/booking_detail.html', context)
 
 
# ── Confirm booking ───────────────────────────────────────────
@role_required(allowed_roles=["service_provider"])
@require_POST
def provider_confirm_booking(request, pk):
    provider = get_object_or_404(ServiceProvider, user=request.user)
    booking  = get_object_or_404(Bookings, pk=pk, provider=provider, bookingStatus='pending')
    booking.bookingStatus = 'confirmed'
    booking.save()
    Notification.objects.create(
        user=booking.customer.user, notificationType='booking_confirmed',
        title='Booking Confirmed',
        message=f'Your booking #{booking.bookingId} for {booking.service.serviceName} '
                f'at {provider.garageName} has been confirmed.',
    )
    messages.success(request, f'Booking #{booking.bookingId} confirmed.')
    return redirect('provider_bookings')
 
 
# ── Start service ─────────────────────────────────────────────
@role_required(allowed_roles=["service_provider"])
@require_POST
def provider_start_booking(request, pk):
    provider = get_object_or_404(ServiceProvider, user=request.user)
    booking  = get_object_or_404(Bookings, pk=pk, provider=provider, bookingStatus='confirmed')
    booking.bookingStatus = 'in_progress'
    booking.save()
    messages.success(request, f'Booking #{booking.bookingId} is now in progress.')
    return redirect('provider_bookings')
 
 
# ── Complete booking ──────────────────────────────────────────
@role_required(allowed_roles=["service_provider"])
@require_POST
def provider_complete_booking(request, pk):
    provider = get_object_or_404(ServiceProvider, user=request.user)
    booking  = get_object_or_404(Bookings, pk=pk, provider=provider, bookingStatus='in_progress')
    booking.bookingStatus = 'completed'
    booking.save()
    Notification.objects.create(
        user=booking.customer.user, notificationType='service_completed',
        title='Service Completed',
        message=f'Your {booking.service.serviceName} service by {provider.garageName} '
                f'is complete. Please leave a review!',
    )
    messages.success(request, f'Booking #{booking.bookingId} marked as completed. Generate invoice now.')
    return redirect('provider_invoice_generate', booking_pk=booking.bookingId)
 
 
# ============================================================
#  3. MY SERVICES  —  /serviceProvider/services/
# ============================================================
@role_required(allowed_roles=["service_provider"])
def provider_services(request):
    provider = get_object_or_404(ServiceProvider, user=request.user)
    services = Services.objects.filter(providerId=provider).order_by('serviceName')
    context  = {
        **get_provider_context(request),
        'active':   'services',
        'services': services,
    }
    return render(request, 'garage/Provider/services.html', context)
 
 
# ── Save / edit service ───────────────────────────────────────
@role_required(allowed_roles=["service_provider"])
@require_POST
def provider_service_save(request):
    provider    = get_object_or_404(ServiceProvider, user=request.user)
    service_id  = request.POST.get('service_id', '').strip()
    name        = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    price       = request.POST.get('price', 0)
    duration    = request.POST.get('duration') or None
    available   = request.POST.get('available', 'true') == 'true'
 
    if not name:
        messages.error(request, 'Service name is required.')
        return redirect('provider_services')
 
    if service_id:
        svc = get_object_or_404(Services, pk=service_id, providerId=provider)
        svc.serviceName        = name
        svc.serviceDescription = description
        svc.servicePrice       = price
        svc.estimatedDuration  = duration
        svc.isAvailable        = available
        svc.save()
        messages.success(request, f'"{name}" updated successfully.')
    else:
        Services.objects.create(
            providerId         = provider,
            serviceName        = name,
            serviceDescription = description,
            servicePrice       = price,
            estimatedDuration  = duration,
            isAvailable        = available,
        )
        messages.success(request, f'"{name}" added successfully.')
 
    return redirect('provider_services')
 
 
# ── Delete service ────────────────────────────────────────────
@role_required(allowed_roles=["service_provider"])
@require_POST
def provider_service_delete(request, pk):
    provider = get_object_or_404(ServiceProvider, user=request.user)
    svc      = get_object_or_404(Services, pk=pk, providerId=provider)
    svc.delete()
    messages.success(request, f'"{svc.serviceName}" deleted.')
    return redirect('provider_services')
 
 
# ============================================================
#  4. REVIEWS  —  /serviceProvider/reviews/
# ============================================================
@role_required(allowed_roles=["service_provider"])
def provider_reviews(request):
    provider = get_object_or_404(ServiceProvider, user=request.user)
    reviews  = (
        Review.objects
        .filter(provider=provider)
        .select_related('customer__user', 'booking__service')
        .order_by('-createdAt')
    )
 
    total   = reviews.count()
    avg_r   = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    avg_rating = round(avg_r, 1)
    positive   = reviews.filter(rating__gte=4).count()
    positive_pct = round((positive / total * 100) if total else 0)
    flagged_count = reviews.filter(rating__lte=2).count()
 
    paginator   = Paginator(reviews, 10)
    review_page = paginator.get_page(request.GET.get('page', 1))
 
    context = {
        **get_provider_context(request),
        'active':        'reviews',
        'reviews':       review_page,
        'avg_rating':    avg_rating,
        'positive_pct':  positive_pct,
        'flagged_count': flagged_count,
    }
    return render(request, 'garage/Provider/reviews.html', context)
 
 
# ============================================================
#  5. EARNINGS  —  /serviceProvider/earnings/
# ============================================================
@role_required(allowed_roles=["service_provider"])
def provider_earnings(request):
    provider = get_object_or_404(ServiceProvider, user=request.user)
    today    = date.today()
 
    payments_qs = (
        Payments.objects
        .filter(booking__provider=provider)
        .select_related('booking__customer__user', 'booking__service')
        .order_by('-paymentDate')
    )
    totals = payments_qs.aggregate(
        total_earned   = Sum('amount', filter=Q(paymentStatus='completed')),
        pending_amount = Sum('amount', filter=Q(paymentStatus='pending')),
    )
    monthly_revenue = (
        payments_qs
        .filter(paymentStatus='completed',
                paymentDate__month=today.month,
                paymentDate__year=today.year)
        .aggregate(total=Sum('amount'))['total'] or 0
    )
    total_invoices = Invoice.objects.filter(booking__provider=provider).count()
 
    paginator    = Paginator(payments_qs, 12)
    payment_page = paginator.get_page(request.GET.get('page', 1))
 
    context = {
        **get_provider_context(request),
        'active':           'earnings',
        'payments':         payment_page,
        'total_earned':     totals['total_earned']   or 0,
        'pending_amount':   totals['pending_amount'] or 0,
        'monthly_revenue':  monthly_revenue,
        'total_invoices':   total_invoices,
    }
    return render(request, 'garage/Provider/earnings.html', context)
 
 
# ============================================================
#  6. NOTIFICATIONS  —  /serviceProvider/notifications/
# ============================================================
@role_required(allowed_roles=["service_provider"])
def provider_notifications(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-createdAt')
    total  = notifs.count()
    read   = notifs.filter(isRead=True).count()
    unread = notifs.filter(isRead=False).count()
    open_rate = round((read / total * 100) if total else 0)
 
    paginator  = Paginator(notifs, 15)
    notif_page = paginator.get_page(request.GET.get('page', 1))
 
    context = {
        **get_provider_context(request),
        'active':        'notifications',
        'notifications': notif_page,
        'total_notifs':  total,
        'read_notifs':   read,
        'open_rate':     open_rate,
    }
    return render(request, 'garage/Provider/notifications.html', context)
 
 
@role_required(allowed_roles=["service_provider"])
def provider_notification_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.isRead = True
    notif.save()
    return redirect('provider_notifications')
 
 
@role_required(allowed_roles=["service_provider"])
def provider_notifications_read_all(request):
    Notification.objects.filter(user=request.user, isRead=False).update(isRead=True)
    messages.success(request, 'All notifications marked as read.')
    return redirect('provider_notifications')
 
 
# ============================================================
#  7. PROFILE  —  /serviceProvider/profile/
# ============================================================
@role_required(allowed_roles=["service_provider"])
def provider_profile(request):
    provider = ServiceProvider.objects.filter(user=request.user).first()
 
    if request.method == 'POST':
        action = request.POST.get('action', 'garage')
 
        if action == 'garage':
            if not provider:
                provider = ServiceProvider(user=request.user)
            provider.garageName  = request.POST.get('garage_name', '').strip()
            provider.description = request.POST.get('description', '').strip()
            provider.location    = request.POST.get('location', '').strip()
            lat = request.POST.get('latitude', '')
            lng = request.POST.get('longitude', '')
            provider.latitude    = float(lat) if lat else None
            provider.longitude   = float(lng) if lng else None
            ot = request.POST.get('opening_time')
            ct = request.POST.get('closing_time')
            if ot: provider.openingTime = ot
            if ct: provider.closingTime = ct
            if 'garage_image' in request.FILES:
                provider.garageImage = request.FILES['garage_image']
            provider.save()
            messages.success(request, 'Garage info updated successfully!')
 
        elif action == 'account':
            request.user.first_name = request.POST.get('first_name', '').strip()
            request.user.last_name  = request.POST.get('last_name', '').strip()
            if hasattr(request.user, 'mobile'):
                request.user.mobile = request.POST.get('mobile', '').strip()
            request.user.save()
            messages.success(request, 'Account info updated!')
 
        elif action == 'password':
            cur  = request.POST.get('current_password', '')
            new  = request.POST.get('new_password', '')
            conf = request.POST.get('confirm_password', '')
            if not request.user.check_password(cur):
                messages.error(request, 'Current password is incorrect.')
            elif new != conf:
                messages.error(request, 'Passwords do not match.')
            elif len(new) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
            else:
                request.user.set_password(new)
                request.user.save()
                messages.success(request, 'Password updated! Please log in again.')
                return redirect('login')
 
        return redirect('provider_profile')
 
    total_bookings = Bookings.objects.filter(provider=provider).count() if provider else 0
    services_count = Services.objects.filter(providerId=provider).count() if provider else 0
 
    context = {
        **get_provider_context(request),
        'active':         'profile',
        'user':           request.user,
        'total_bookings': total_bookings,
        'services_count': services_count,
    }
    return render(request, 'garage/Provider/profile.html', context)
 
 
# ============================================================
#  LOGOUT
# ============================================================
def provider_logout(request):
    auth_logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')
 
 
# ============================================================
#  INVOICE VIEWS
# ============================================================
 
def _next_invoice_number(provider):
    """Generate sequential invoice number like INV-2026-001."""
    year  = date.today().year
    count = Invoice.objects.filter(
        booking__provider=provider,
        invoiceDate__year=year
    ).count() + 1
    return f"INV-{year}-{count:03d}"
 
 
# ── Show generate-invoice form ─────────────────────────────────
@role_required(allowed_roles=["service_provider"])
def provider_invoice_generate(request, booking_pk):
    provider = get_object_or_404(ServiceProvider, user=request.user)
    booking  = get_object_or_404(
        Bookings, pk=booking_pk, provider=provider, bookingStatus='completed'
    )
 
    if hasattr(booking, 'invoice') and booking.invoice:
        messages.info(request, 'Invoice already exists. Redirecting to view.')
        return redirect('provider_invoice_view', pk=booking.invoice.invoiceId)
 
    if request.method == 'POST':
        inv_num        = request.POST.get('invoice_number', '').strip()
        gst_pct        = float(request.POST.get('gst_percent', 18))
        gst_amount     = float(request.POST.get('gst_amount', 0))
        discount       = float(request.POST.get('discount_amount', 0))
        total_amount   = float(request.POST.get('total_amount', booking.service.servicePrice))
        pay_method     = request.POST.get('payment_method', 'cash')
        pay_status     = request.POST.get('payment_status', 'completed')
        notes          = request.POST.get('notes', '').strip()
 
        if not inv_num:
            inv_num = _next_invoice_number(provider)
 
        # Create Payment record
        payment = Payments.objects.create(
            booking       = booking,
            amount        = total_amount,
            paymentMethod = pay_method,
            paymentStatus = pay_status,
            transactionId = str(uuid.uuid4())[:12].upper(),
            paymentDate   = timezone.now(),
        )
 
        # Create Invoice record
        invoice = Invoice.objects.create(
            booking        = booking,
            payment        = payment,
            invoiceNumber  = inv_num,
            invoiceDate    = date.today(),
            totalAmount    = total_amount,
            taxAmount      = gst_amount,
            discountAmount = discount,
        )
 
        # Notify customer
        Notification.objects.create(
            user             = booking.customer.user,
            notificationType = 'payment_received',
            title            = 'Invoice Generated',
            message          = (
                f'Invoice {inv_num} has been generated for your '
                f'{booking.service.serviceName} booking. '
                f'Total: ₹{total_amount}.'
            ),
        )
 
        messages.success(request, f'Invoice {inv_num} generated successfully!')
        return redirect('provider_invoice_view', pk=invoice.invoiceId)
 
    context = {
        **get_provider_context(request),
        'active':            'earnings',
        'booking':           booking,
        'user':              request.user,
        'today':             date.today().strftime('%d %b %Y'),
        'next_invoice_num':  _next_invoice_number(provider).split('-')[-1],
    }
    return render(request, 'garage/Provider/invoice_generate.html', context)
 
 
# ── View / preview invoice ─────────────────────────────────────
@role_required(allowed_roles=["service_provider"])
def provider_invoice_view(request, pk):
    provider = get_object_or_404(ServiceProvider, user=request.user)
    invoice  = get_object_or_404(Invoice, pk=pk, booking__provider=provider)
    context  = {
        **get_provider_context(request),
        'active':   'earnings',
        'invoice':  invoice,
        'provider': provider,
        'user':     request.user,
        'today':    date.today().strftime('%d %b %Y'),
    }
    return render(request, 'garage/Provider/invoice_view.html', context)
 
 
# ── Download invoice as CSV ────────────────────────────────────
@role_required(allowed_roles=["service_provider"])
def provider_invoice_download(request, pk):
    import csv as csv_module
    provider = get_object_or_404(ServiceProvider, user=request.user)
    invoice  = get_object_or_404(Invoice, pk=pk, booking__provider=provider)
    b = invoice.booking
 
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="{invoice.invoiceNumber}.csv"'
    )
    writer = csv_module.writer(response)
    writer.writerow(['E-GARAGE — TAX INVOICE'])
    writer.writerow([])
    writer.writerow(['Invoice No.',    invoice.invoiceNumber])
    writer.writerow(['Invoice Date',   invoice.invoiceDate])
    writer.writerow(['Booking ID',     f'#BK{b.bookingId}'])
    writer.writerow([])
    writer.writerow(['FROM (Provider)', provider.garageName])
    writer.writerow(['Location',        provider.location])
    writer.writerow(['Email',           request.user.email])
    writer.writerow([])
    writer.writerow(['TO (Customer)',   b.customer.user.get_full_name()])
    writer.writerow(['Email',           b.customer.user.email])
    writer.writerow(['Vehicle',         b.customer.vehicleNumber])
    writer.writerow([])
    writer.writerow(['DESCRIPTION',     'AMOUNT'])
    writer.writerow([b.service.serviceName, f'₹{b.service.servicePrice}'])
    writer.writerow(['GST',             f'₹{invoice.taxAmount}'])
    writer.writerow(['Discount',        f'₹{invoice.discountAmount}'])
    writer.writerow(['TOTAL',           f'₹{invoice.totalAmount}'])
    return response
 
 
# ── Print-friendly invoice page ───────────────────────────────
@role_required(allowed_roles=["service_provider"])
def provider_invoice_print(request, pk):
    provider = get_object_or_404(ServiceProvider, user=request.user)
    invoice  = get_object_or_404(Invoice, pk=pk, booking__provider=provider)
    context  = {
        'invoice':  invoice,
        'provider': provider,
        'user':     request.user,
        'today':    date.today().strftime('%d %b %Y'),
    }
    return render(request, 'garage/Provider/invoice_print.html', context)
 
 
# ── Export all invoices as CSV ────────────────────────────────
@role_required(allowed_roles=["service_provider"])
def provider_invoices_export(request):
    import csv as csv_module
    provider = get_object_or_404(ServiceProvider, user=request.user)
    invoices = Invoice.objects.filter(
        booking__provider=provider
    ).select_related('booking__customer__user', 'booking__service').order_by('-invoiceDate')
 
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="{provider.garageName}_invoices.csv"'
    )
    writer = csv_module.writer(response)
    writer.writerow(['Invoice No', 'Date', 'Booking', 'Customer', 'Service', 'Vehicle',
                     'Service Amount', 'GST', 'Discount', 'Total', 'Payment Status'])
    for inv in invoices:
        b = inv.booking
        writer.writerow([
            inv.invoiceNumber,
            inv.invoiceDate,
            f'#BK{b.bookingId}',
            b.customer.user.get_full_name(),
            b.service.serviceName,
            b.customer.vehicleNumber,
            b.service.servicePrice,
            inv.taxAmount,
            inv.discountAmount,
            inv.totalAmount,
            inv.payment.paymentStatus if inv.payment else 'No Payment',
        ])
    return response
 
 
# ── Updated earnings view (adds invoices list) ────────────────
@role_required(allowed_roles=["service_provider"])
def provider_earnings(request):
    provider = get_object_or_404(ServiceProvider, user=request.user)
    today    = date.today()
 
    payments_qs = (
        Payments.objects
        .filter(booking__provider=provider)
        .select_related('booking__customer__user', 'booking__service')
        .order_by('-paymentDate')
    )
    totals = payments_qs.aggregate(
        total_earned   = Sum('amount', filter=Q(paymentStatus='completed')),
        pending_amount = Sum('amount', filter=Q(paymentStatus='pending')),
    )
    monthly_revenue = (
        payments_qs
        .filter(paymentStatus='completed',
                paymentDate__month=today.month,
                paymentDate__year=today.year)
        .aggregate(total=Sum('amount'))['total'] or 0
    )
 
    invoices_qs = (
        Invoice.objects
        .filter(booking__provider=provider)
        .select_related('booking__customer__user', 'booking__service', 'payment')
        .order_by('-invoiceDate')
    )
    total_invoices = invoices_qs.count()
 
    pay_paginator = Paginator(payments_qs, 10)
    inv_paginator = Paginator(invoices_qs, 10)
 
    context = {
        **get_provider_context(request),
        'active':           'earnings',
        'payments':         pay_paginator.get_page(request.GET.get('pay_page', 1)),
        'invoices':         inv_paginator.get_page(request.GET.get('inv_page', 1)),
        'total_earned':     totals['total_earned']   or 0,
        'pending_amount':   totals['pending_amount'] or 0,
        'monthly_revenue':  monthly_revenue,
        'total_invoices':   total_invoices,
    }
    return render(request, 'garage/Provider/earnings.html', context)