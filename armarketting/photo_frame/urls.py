"""
URL configuration for armarketting project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from photo_frame import views
from django.views.generic import TemplateView

from django.urls import include


urlpatterns = [
    path('qr/userex/<hasheduserid>', views.user_experience, name='userex'),
    path('scanner', views.scanner, name='scanner'),
    path('qr/<int:frameuserid>', views.generate_qr, name='qr'),
    # path('aboutus', views.aboutus, name='aboutus'),
    path('client-signup', views.client_signup, name='client-signup'),
    path('enterotp', views.otp, name='enterotp'),
    path('client-password', views.client_signup_password, name='client-password'),
    path('forget-password', views.client_forget_pswd, name='forget-password'),
    path('otp', views.otp_forget, name='otp'),
    path('password', views.client_signup_password_forget, name='password'),
    path('client-form', views.client_form, name='client-form'),
    path('signin', views.client_signin, name='signin'),
    path('dashboard', views.user_dashboard, name='dashboard'),
    path('customer-data/<int:id>', views.customer_data, name='customer-data'),
    path('customer-data-search/<int:id>', views.user_dashboard_search, name='customer-data-search'),
    path('add-frame/<int:id>', views.add_frame, name='add-frame'),
    path('paymenthandler/', views.paymenthandler, name='paymenthandler'),
    path("payment",views.payment, name='payment'),
    path("logout/", views.user_logout, name="logout"),
    path("cancellation-policy/", views.cancellation_policy, name="cancellation-policy"),
    
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
