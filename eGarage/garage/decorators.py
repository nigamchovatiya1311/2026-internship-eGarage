from django.shortcuts import redirect
from django.http import HttpResponse
from django.contrib import messages
from functools import wraps


def role_required(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper_func(request, *args, **kwargs):

            # Session expired or never logged in
            if not request.user.is_authenticated:
                messages.warning(
                    request,
                    'Your session has expired. Please log in again.'
                )
                return redirect('login')

            # Logged in with correct role
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            # Logged in but wrong role — redirect to own dashboard
            messages.error(request, 'You are not authorized to view this page.')
            role_home = {
                'admin':            'admin_overview',
                'service_provider': 'provider_overview',
                'customer':         'customer_home',
            }
            return redirect(role_home.get(request.user.role, 'login'))

        return wrapper_func
    return decorator