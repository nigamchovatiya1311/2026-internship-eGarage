from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('signup/',     views.userSignupView, name='signup'),
    path('otp-verify/', views.otpVerifyView,  name='otp_verify'),
    path('otp-resend/', views.resendOtpView,  name='otp_resend'),
    path('login/',      views.userLoginView,  name='login'),
]