from django.urls import path
from .import views


urlpatterns = [
    path("admin/",views.admindashboard,name="admin_dashboard"),
    path("customer/",views.customerdashboard,name="customer_dashboard"),
    path("serviceProvider/",views.serviceProviderdashboard, name="serviceProvider_dashboard"),

]