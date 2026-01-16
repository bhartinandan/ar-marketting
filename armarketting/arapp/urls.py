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
from arapp import views
from django.views.generic import TemplateView

from django.urls import include


urlpatterns = [
    #basic urls
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('contact/', views.contact, name='contact'),
    path('aboutus/', views.aboutus, name='aboutus'),
    path('privacypolicy/', views.privacypolicy, name='privacypolicy'),
    path('term-condition/', views.term_and_condition, name='term-condition'),

    #services urls
    path('staff-signin', views.staff_signin, name='staff-signin'),
    path('staff-dashboard', views.staff_dashboard, name='staff-dashboard'),
    path('frame-dashboard', views.frame_dashboard, name='frame-dashboard'),
    path('end-consumer-details/<str:id>', views.end_consumer_details, name='end-consumer-details'),
    path('create-client', views.create_client, name='create-client'),
    path('client-details/<str:id>', views.client_details, name='client-details'),
    path('create-service/<str:id>', views.create_service, name='create-service'),
    path('staff-logout', views.staff_logout, name='staff-logout'),

    # Aliveframe AR Games
    path('ar-burger-game-landing/<slug:hashid>', views.ar_burger_game_landing, name='ar-burger-game-landing'),
    path('burger-game/<slug:name>/<slug:hashid>', views.burger_game, name='burger-game'),
    path('update-high-score', views.update_burger_score, name='update-high-score'),


    #client signin urls 
    path('signin', views.client_signin, name='signin'),
    path('clientid', views.client_forget_id, name='clientid'),
    path('clientotp', views.client_otp_forget, name='clientotp'),
    path('clientpassword', views.client_signup_password_forget, name='clientpassword'),
    path('dashboard', views.dashboard, name='dashboard'),
    path('service-statistics/<str:id>', views.service_statitiscs, name='service-statistics'),
    path('client-logout', views.client_logout, name='client-logout'),
    path('staff-logout', views.staff_logout, name='staff-logout'),
    path('blog', views.blog_page, name='blog-page'),

    path('assets/<int:id>', views.assets, name='assets'),
    path('userex/<str:hasheduserid>', views.user_ex, name='userex'),
    path('qr/<int:frameuserid>', views.generate_qr, name='qr'),

]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
