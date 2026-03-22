from django.shortcuts import render,redirect,HttpResponse
from django.contrib.auth import authenticate,login
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
import os
from garage.models import CustomerProfile 


def send_welcome_email(user):
    subject = "Welcome to eGarage!"

    html_content = render_to_string('core/welcome_email.html', {
        'username': user.first_name + user.last_name,
        'email': user.email,
    })
    text_content = strip_tags(html_content)

    # Build MIME structure manually for inline image support
    msg_root = MIMEMultipart('related')
    msg_root['Subject'] = subject
    msg_root['From'] = settings.DEFAULT_FROM_EMAIL
    msg_root['To'] = user.email

    # Attach alternative (plain + html)
    msg_alternative = MIMEMultipart('alternative')
    msg_root.attach(msg_alternative)

    msg_alternative.attach(MIMEText(text_content, 'plain'))
    msg_alternative.attach(MIMEText(html_content, 'html'))

    # Attach inline image with Content-ID
    image_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'welcome_egarage.png')
    if os.path.exists(image_path):
        with open(image_path, 'rb') as img_file:
            mime_image = MIMEImage(img_file.read())
            mime_image.add_header('Content-ID', '<welcome_egarage>')
            mime_image.add_header('Content-Disposition', 'inline', filename='welcome_egarage.png')
            msg_root.attach(mime_image)

    # Send using Django's connection
    connection = get_connection()
    connection.open()
    connection.connection.sendmail(
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        msg_root.as_string()
    )
    connection.close()




def userSignupView(request):
    if request.method == "POST":
        form = UserSignUpForm(request.POST or None)
        if form.is_valid():
            user = form.save()

            # Auto-create CustomerProfile on every new customer signup
            if user.role == 'customer':
                CustomerProfile.objects.create(user=user)

            send_welcome_email(user)
            return redirect('login')
        else:
            return render(request, 'core/signup.html', {'form': form})
    else:
        form = UserSignUpForm()
        return render(request, 'core/signup.html', {'form': form})



def userLoginView(request):
    if request.method == "POST":
        form = UserLoginForm(request.POST or None)

        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)

            if user:
                login(request, user)
                if user.role == 'admin':
                    return redirect('admin_dashboard')
                elif user.role == 'customer':
                    return redirect('customer_home')
                elif user.role == 'service_provider':
                    return redirect('serviceProvider_dashboard')
            
            # Add error message when credentials are wrong
            form.add_error(None, 'Invalid email or password.')

        # This return was MISSING — caused the ValueError
        return render(request, 'core/login.html', {'form': form})

    else:
        form = UserLoginForm()
        return render(request, 'core/login.html', {'form': form})    