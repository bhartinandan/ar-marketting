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
from loyalty import views
from django.views.generic import TemplateView

from django.urls import include


urlpatterns = [
    #business side urls
    # path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('', views.signin_signup, name='signin_signup'),
    path("logout", views.logout_user, name="logout"),
    path('signin', views.signin_signup, name='signin_signup'),
    path('send-otp', views.send_otp, name="send_otp"),
    path('loyalty-otp-verification', views.otp_verification, name='otp_verification'),
    path('business-welcome', views.welcome_business, name='welcome'),
    path('business-dashboard', views.business_dashboard, name='business_dashboard'),
    path(
        "approve-visit/<int:visit_id>/",
        views.approve_visit,
        name="approve_visit"
    ),

    path(
        "reject-visit/<int:visit_id>/",
        views.reject_visit,
        name="reject_visit"
    ),
    path('business-profile', views.business_profile, name='business_profile'),
    path('update-business-profile',views.update_business_profile, name="update_business_profile"),
    path('create-offer', views.create_offer, name='create_offer'),
    path('create-stamp-card', views.create_stamp_card, name='create_stamp_card'),
    path('customers-list', views.customers_list, name='customers_list'),
    path('winners-list', views.winners_list, name='winners_list'),
    path('business-help', views.business_help, name='business_help'),
    path('payment', views.payment, name='payment'),
    path('business-privacy-policy', views.business_privacy_policy, name='business_privacy_policy'),
    path("save-rewards", views.save_rewards, name="save_rewards"),
    path("payments/create-order/", views.create_order, name="create_order"),
    path("payments/verify-payment/", views.verify_payment, name="verify_payment"),
    #customer side urls
    path('customer-dashboard/<slug:hash_id>', views.customer_dashboard, name='customer_dashboard'),
    path('customer-name/<slug:hash_id>',views.customer_name, name='customer_name'),
    path('customer-profile/<slug:hash_id>', views.customer_profile, name='customer_profile'),
    path('customer-rewards/<slug:hash_id>', views.customer_rewards, name='customer_rewards'),
    path('customer-explore/<slug:hash_id>', views.customer_explore, name='customer_explore'), 
    path('customer-scanner/<slug:hash_id>', views.customer_scanner, name='customer_scanner'),
    path('customer-scanned-success/<slug:hash_id>', views.customer_scanned_success, name='customer_scanned_success'),
    path('stamp-card-details/<slug:hash_id>/<int:reward_id>', views.stamp_card_details, name='stamp_card_details'),
    path("reward-approval-request/<slug:customer_visit_hash_id>", views.reward_approval_request, name="reward_approval_request"),
    path("accept-claim/<int:visit_id>", views.accept_claim, name="accept_claim"),
    path("reject-claim/<int:visit_id>", views.reject_claim, name="reject_claim"),
    
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
