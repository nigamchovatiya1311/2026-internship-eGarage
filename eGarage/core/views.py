from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth import authenticate, login
from .forms import UserSignUpForm, UserLoginForm
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from django.core.mail import get_connection
from django.utils import timezone
from django.contrib.auth import get_user_model
import os
import random
from garage.models import CustomerProfile

User = get_user_model()


# ─────────────────────────────────────────────
#  Helper: Send Welcome Email (existing logic)
# ─────────────────────────────────────────────
def send_welcome_email(user):
    subject = "Welcome to eGarage!"

    html_content = render_to_string('core/welcome_email.html', {
        'username': user.first_name + user.last_name,
        'email': user.email,
    })
    text_content = strip_tags(html_content)

    msg_root = MIMEMultipart('related')
    msg_root['Subject'] = subject
    msg_root['From'] = settings.DEFAULT_FROM_EMAIL
    msg_root['To'] = user.email

    msg_alternative = MIMEMultipart('alternative')
    msg_root.attach(msg_alternative)
    msg_alternative.attach(MIMEText(text_content, 'plain'))
    msg_alternative.attach(MIMEText(html_content, 'html'))

    image_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'welcome_egarage.png')
    if os.path.exists(image_path):
        with open(image_path, 'rb') as img_file:
            mime_image = MIMEImage(img_file.read())
            mime_image.add_header('Content-ID', '<welcome_egarage>')
            mime_image.add_header('Content-Disposition', 'inline', filename='welcome_egarage.png')
            msg_root.attach(mime_image)

    connection = get_connection()
    connection.open()
    connection.connection.sendmail(
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        msg_root.as_string()
    )
    connection.close()


# ─────────────────────────────────────────────
#  Helper: Send OTP Email
# ─────────────────────────────────────────────
def send_otp_email(user, otp):
    subject = "eGarage – Your OTP Verification Code"

    html_content = render_to_string('core/otp_email.html', {
        'username': user.first_name,
        'otp': otp,
    })
    text_content = strip_tags(html_content)

    msg_root = MIMEMultipart('related')
    msg_root['Subject'] = subject
    msg_root['From'] = settings.DEFAULT_FROM_EMAIL
    msg_root['To'] = user.email

    msg_alternative = MIMEMultipart('alternative')
    msg_root.attach(msg_alternative)
    msg_alternative.attach(MIMEText(text_content, 'plain'))
    msg_alternative.attach(MIMEText(html_content, 'html'))

    connection = get_connection()
    connection.open()
    connection.connection.sendmail(
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        msg_root.as_string()
    )
    connection.close()


# ─────────────────────────────────────────────
#  Helper: Generate 6-digit OTP
# ─────────────────────────────────────────────
def generate_otp():
    return str(random.randint(100000, 999999))


# ─────────────────────────────────────────────
#  View: Signup
#  After valid signup → generate OTP → send email → redirect to OTP page
# ─────────────────────────────────────────────
def userSignupView(request):
    if request.method == "POST":
        form = UserSignUpForm(request.POST or None)
        if form.is_valid():
            user = form.save()

            # Auto-create CustomerProfile for customer role
            if user.role == 'customer':
                CustomerProfile.objects.create(user=user)

            # Send welcome email
            send_welcome_email(user)

            # Generate OTP and store in session
            otp = generate_otp()
            request.session['otp_code']       = otp
            request.session['otp_user_id']    = user.id
            request.session['otp_created_at'] = timezone.now().isoformat()

            # Send OTP email
            send_otp_email(user, otp)

            return redirect('otp_verify')
        else:
            return render(request, 'core/signup.html', {'form': form})
    else:
        form = UserSignUpForm()
        return render(request, 'core/signup.html', {'form': form})


# ─────────────────────────────────────────────
#  View: OTP Verification
#  Validates OTP from session → redirect to login
# ─────────────────────────────────────────────
def otpVerifyView(request):
    # Guard: if no OTP session exists, send back to signup
    if 'otp_code' not in request.session:
        return redirect('signup')

    if request.method == "POST":
        entered_otp = request.POST.get('otp', '').strip()

        stored_otp      = request.session.get('otp_code')
        otp_created_at  = request.session.get('otp_created_at')
        user_id         = request.session.get('otp_user_id')

        # Check OTP expiry (10 minutes)
        created_at = timezone.datetime.fromisoformat(otp_created_at)
        if timezone.is_naive(created_at):
            created_at = timezone.make_aware(created_at)

        time_elapsed = (timezone.now() - created_at).total_seconds()

        if time_elapsed > 600:  # 10 minutes
            # Clear expired OTP session data
            _clear_otp_session(request)
            return render(request, 'core/otp_verify.html', {
                'error': 'OTP has expired. Please sign up again.',
                'expired': True,
            })

        if entered_otp == stored_otp:
            # OTP matched — clear session data and redirect to login
            _clear_otp_session(request)
            return redirect('login')
        else:
            return render(request, 'core/otp_verify.html', {
                'error': 'Invalid OTP. Please try again.',
            })

    return render(request, 'core/otp_verify.html', {})


# ─────────────────────────────────────────────
#  View: Resend OTP
# ─────────────────────────────────────────────
def resendOtpView(request):
    user_id = request.session.get('otp_user_id')

    if not user_id:
        return redirect('signup')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return redirect('signup')

    # Generate fresh OTP and update session
    otp = generate_otp()
    request.session['otp_code']       = otp
    request.session['otp_created_at'] = timezone.now().isoformat()

    send_otp_email(user, otp)

    return render(request, 'core/otp_verify.html', {
        'success': 'A new OTP has been sent to your email.',
    })


# ─────────────────────────────────────────────
#  View: Login
# ─────────────────────────────────────────────
def userLoginView(request):
    if request.method == "POST":
        form = UserLoginForm(request.POST or None)

        if form.is_valid():
            email    = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user     = authenticate(request, email=email, password=password)

            if user:
                login(request, user)
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role == 'customer':
                    return redirect('customer_home')
                elif user.role == 'service_provider':
                    return redirect('serviceProvider_dashboard')

            form.add_error(None, 'Invalid email or password.')

        return render(request, 'core/login.html', {'form': form})

    else:
        form = UserLoginForm()
        return render(request, 'core/login.html', {'form': form})


# ─────────────────────────────────────────────
#  Internal helper
# ─────────────────────────────────────────────
def _clear_otp_session(request):
    for key in ('otp_code', 'otp_user_id', 'otp_created_at'):
        request.session.pop(key, None)