from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.

@login_required(login_url="login")
def admindashboard(request):
    return render(request, "garage/admin_dashboard.html")

@login_required(login_url="login")
def customerdashboard(request):
    return render(request, "garage/customer_dashboard.html")    

@login_required(login_url="login")
def serviceProviderdashboard(request):
    return render(request, "garage/serviceprovider_dashboard.html")