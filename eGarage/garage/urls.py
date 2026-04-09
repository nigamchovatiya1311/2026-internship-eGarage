from django.urls import path
from . import views

urlpatterns = [

    # ══════════════════════════════════════════════════════
    #  DASHBOARD ENTRY POINTS
    # ══════════════════════════════════════════════════════
    path('admin/', views.admindashboard, name='admin_dashboard'),
    path('serviceProvider/', views.serviceProviderdashboard, name='serviceProvider_dashboard'),

    # ══════════════════════════════════════════════════════
    #  ADMIN — OVERVIEW
    # ══════════════════════════════════════════════════════
    path('admin/overview/', views.overview, name='admin_overview'),

    # ══════════════════════════════════════════════════════
    #  ADMIN — USERS
    # ══════════════════════════════════════════════════════
    path('admin/users/', views.manage_users, name='admin_users'),
    path('admin/users/add/', views.add_user, name='admin_user_add'),
    path('admin/users/<int:pk>/block/', views.block_user, name='block_user'),
    path('admin/users/<int:pk>/unblock/', views.unblock_user, name='unblock_user'),
    path('admin/users/<int:pk>/approve/', views.approve_user, name='approve_user'),

    # ══════════════════════════════════════════════════════
    #  ADMIN — SERVICE PROVIDERS
    # ══════════════════════════════════════════════════════
    path('admin/providers/', views.service_providers, name='admin_providers'),
    path('admin/providers/<int:pk>/approve/', views.approve_provider, name='approve_provider'),
    path('admin/providers/<int:pk>/reject/', views.reject_provider, name='reject_provider'),

    # ══════════════════════════════════════════════════════
    #  ADMIN — CUSTOMER PROFILES
    # ══════════════════════════════════════════════════════
    path('admin/customers/', views.customer_profiles, name='admin_customers'),

    # ══════════════════════════════════════════════════════
    #  ADMIN — SERVICES
    # ══════════════════════════════════════════════════════
    path('admin/services/', views.services, name='admin_services'),
    path('admin/services/save/', views.save_service, name='admin_service_save'),

    # ══════════════════════════════════════════════════════
    #  ADMIN — BOOKINGS
    # ══════════════════════════════════════════════════════
    path('admin/bookings/', views.monitor_bookings, name='admin_bookings'),

    # ══════════════════════════════════════════════════════
    #  ADMIN — PAYMENTS
    # ══════════════════════════════════════════════════════
    path('admin/payments/', views.payments, name='admin_payments'),

    # ══════════════════════════════════════════════════════
    #  ADMIN — INVOICES
    # ══════════════════════════════════════════════════════
    path('admin/invoices/', views.invoices, name='admin_invoices'),
    path('admin/invoices/<int:pk>/download/', views.download_invoice, name='download_invoice'),

    # ══════════════════════════════════════════════════════
    #  ADMIN — REVIEWS
    # ══════════════════════════════════════════════════════
    path('admin/reviews/', views.reviews, name='admin_reviews'),
    path('admin/reviews/<int:pk>/flag/', views.flag_review, name='flag_review'),
    path('admin/reviews/<int:pk>/delete/', views.delete_review, name='delete_review'),

    # ══════════════════════════════════════════════════════
    #  ADMIN — NOTIFICATIONS
    # ══════════════════════════════════════════════════════
    path('admin/notifications/', views.notifications, name='admin_notifications'),
    path('admin/notifications/send/', views.send_notification, name='send_notification'),
    path('admin/notifications/read-all/', views.mark_all_read, name='mark_all_read'),
    path('admin/notifications/<int:pk>/read/', views.mark_read, name='mark_read'),

    # ══════════════════════════════════════════════════════
    #  ADMIN — DISPUTES
    # ══════════════════════════════════════════════════════
    path('admin/disputes/', views.disputes, name='admin_disputes'),
    path('admin/disputes/<int:pk>/resolve/', views.resolve_dispute, name='resolve_dispute'),

    # ══════════════════════════════════════════════════════
    #  ADMIN — ANALYTICS
    # ══════════════════════════════════════════════════════
    path('admin/analytics/', views.analytics, name='admin_analytics'),

    # ══════════════════════════════════════════════════════
    #  ADMIN — REPORTS
    # ══════════════════════════════════════════════════════
    path('admin/reports/', views.generate_reports, name='admin_reports'),
    path('admin/reports/export/<str:report_type>/<str:fmt>/', views.export_report, name='export_report'),

    # ══════════════════════════════════════════════════════
    #  ADMIN — DELETE + LOGOUT
    # ══════════════════════════════════════════════════════
    path('admin/delete/', views.generic_delete, name='generic_delete'),
    path('admin/logout/', views.admin_logout, name='admin_logout'),

    # ══════════════════════════════════════════════════════
    #  CUSTOMER — HOME
    # ══════════════════════════════════════════════════════
    path('customer/home/', views.customer_home, name='customer_home'),

    # ══════════════════════════════════════════════════════
    #  CUSTOMER — BOOK SERVICE
    # ══════════════════════════════════════════════════════
    path('customer/book/', views.book_service, name='book_service'),

    # ══════════════════════════════════════════════════════
    #  CUSTOMER — MY BOOKINGS
    # ══════════════════════════════════════════════════════
    path('customer/bookings/', views.my_bookings, name='my_bookings'),
    path('customer/bookings/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),

    # ══════════════════════════════════════════════════════
    #  CUSTOMER — SERVICE HISTORY
    # ══════════════════════════════════════════════════════
    path('customer/history/', views.service_history, name='service_history'),
    path('customer/history/invoice/<int:pk>/view/', views.customer_invoice_view, name='customer_invoice_view'),
    path('customer/history/invoice/<int:pk>/download/', views.customer_download_invoice, name='customer_download_invoice'),
    path('customer/history/<int:booking_pk>/review/', views.submit_review, name='submit_review'),

    # ══════════════════════════════════════════════════════
    #  CUSTOMER — MY VEHICLE
    # ══════════════════════════════════════════════════════
    path('customer/vehicle/', views.my_vehicle, name='my_vehicle'),

    # ══════════════════════════════════════════════════════
    #  CUSTOMER — PAYMENTS
    # ══════════════════════════════════════════════════════
    path('customer/payments/', views.my_payments, name='my_payments'),

    # ══════════════════════════════════════════════════════
    #  CUSTOMER — NOTIFICATIONS
    # ══════════════════════════════════════════════════════
    path('customer/notifications/', views.customer_notifications, name='customer_notifications'),
    path('customer/notifications/read-all/', views.mark_all_notif_read, name='mark_all_notif_read'),
    path('customer/notifications/<int:pk>/read/', views.mark_notif_read, name='mark_notif_read'),

    # ══════════════════════════════════════════════════════
    #  CUSTOMER — PROFILE + LOGOUT
    # ══════════════════════════════════════════════════════
    path('customer/profile/', views.customer_profile, name='customer_profile'),
    path('customer/logout/', views.customer_logout, name='customer_logout'),

    # ══════════════════════════════════════════════════════
    #  SERVICE PROVIDER — OVERVIEW
    # ══════════════════════════════════════════════════════
    path('serviceProvider/overview/', views.provider_overview, name='provider_overview'),

    # ══════════════════════════════════════════════════════
    #  SERVICE PROVIDER — BOOKINGS (FIXED pk → booking_id)
    # ══════════════════════════════════════════════════════
    path('serviceProvider/bookings/', views.provider_bookings, name='provider_bookings'),
    path('serviceProvider/bookings/<int:booking_id>/', views.provider_booking_detail, name='provider_booking_detail'),
    path('serviceProvider/bookings/<int:booking_id>/confirm/', views.provider_confirm_booking, name='provider_confirm_booking'),
    path('serviceProvider/bookings/<int:booking_id>/start/', views.provider_start_booking, name='provider_start_booking'),
    path('serviceProvider/bookings/<int:booking_id>/complete/', views.provider_complete_booking, name='provider_complete_booking'),

    # ══════════════════════════════════════════════════════
    #  SERVICE PROVIDER — SERVICES
    # ══════════════════════════════════════════════════════
    path('serviceProvider/services/', views.provider_services, name='provider_services'),
    path('serviceProvider/services/save/', views.provider_service_save, name='provider_service_save'),
    path('serviceProvider/services/<int:pk>/delete/', views.provider_service_delete, name='provider_service_delete'),

    # ══════════════════════════════════════════════════════
    #  SERVICE PROVIDER — REVIEWS
    # ══════════════════════════════════════════════════════
    path('serviceProvider/reviews/', views.provider_reviews, name='provider_reviews'),

    # ══════════════════════════════════════════════════════
    #  SERVICE PROVIDER — EARNINGS
    # ══════════════════════════════════════════════════════
    path('serviceProvider/earnings/', views.provider_earnings, name='provider_earnings'),
    path('serviceProvider/earnings/export/', views.provider_earnings_export, name='provider_earnings_export'),

    # ══════════════════════════════════════════════════════
    #  SERVICE PROVIDER — INVOICES (FIXED booking_pk / pk)
    # ══════════════════════════════════════════════════════
    path('serviceProvider/invoice/<int:booking_id>/generate/', views.provider_invoice_generate, name='provider_invoice_generate'),
    path('serviceProvider/invoice/<int:invoice_id>/view/', views.provider_invoice_view, name='provider_invoice_view'),
    path('serviceProvider/invoice/<int:invoice_id>/download/', views.provider_invoice_download, name='provider_invoice_download'),
    path('serviceProvider/invoice/<int:invoice_id>/print/', views.provider_invoice_print, name='provider_invoice_print'),
    path('serviceProvider/invoices/export/', views.provider_invoices_export, name='provider_invoices_export'),

    # ══════════════════════════════════════════════════════
    #  SERVICE PROVIDER — NOTIFICATIONS
    # ══════════════════════════════════════════════════════
    path('serviceProvider/notifications/', views.provider_notifications, name='provider_notifications'),
    path('serviceProvider/notifications/read-all/', views.provider_notifications_read_all, name='provider_notifications_read_all'),
    path('serviceProvider/notifications/<int:pk>/read/', views.provider_notification_read, name='provider_notification_read'),

    # ══════════════════════════════════════════════════════
    #  SERVICE PROVIDER — PROFILE + LOGOUT
    # ══════════════════════════════════════════════════════
    path('serviceProvider/profile/', views.provider_profile, name='provider_profile'),
    path('serviceProvider/profile/save/', views.provider_profile, name='provider_profile_save'),
    path('serviceProvider/logout/', views.provider_logout, name='provider_logout'),
]