from django.utils import timezone
from datetime import datetime, time, timedelta
from venv import logger
from decimal import Decimal
from django.shortcuts import redirect, render
from django.contrib.auth import login, authenticate, logout
from .utils import *
from django.contrib.auth.decorators import login_required,user_passes_test
from loyalty.models import *
from .utils import *
import qrcode
from django.db import transaction
from django.contrib.auth import login
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import F
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.db.models import Prefetch

from collections import defaultdict
from datetime import timedelta
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from django.contrib.auth.models import User, Group
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.http import JsonResponse
import logging
from django.views.decorators.csrf import csrf_exempt


import json

import razorpay

from django.conf import settings

from django.http import JsonResponse

from django.views.decorators.http import require_POST

from django.contrib.auth.decorators import login_required

from django.utils import timezone

from .models import SubscriptionPayment

logger = logging.getLogger(__name__)
# Create your views here.
client = razorpay.Client(
    auth=(
        settings.RAZOR_KEY_ID,
        settings.RAZOR_KEY_SECRET
    )
)
#########################################################################
########################## Business Side Views ##########################
#########################################################################

def is_business(user):
    return user.groups.filter(name='LOYALTY-BUSINESS').exists()

def is_customer(user):
    return user.groups.filter(name='LOYALTY-CUSTOMER').exists()


def logout_user(request):
    """
    Logs out the current user and clears the session.
    """
    business_hash_id = request.session.get("business_hash_id")

    logout(request)

    # Optional: clear any custom session data
    request.session.flush()

    return redirect(f"/loyalty/customer-dashboard/{business_hash_id}")

def signin_signup(request):
    """
    Handles client sign-in.
    """
    next_url = request.GET.get("next")
    print(next_url)
    
    if next_url:
        request.session["next_url"] = next_url

        parts = next_url.strip("/").split("/")

        if "customer-dashboard" in parts:
            index = parts.index("customer-dashboard")
            if len(parts) > index + 1:
                request.session["business_hash_id"] = parts[index + 1]

        elif "customer-scanned-success" in parts:
            index = parts.index("customer-scanned-success")
            if len(parts) > index + 1:
                request.session["business_hash_id"] = parts[index + 1]
    
    if request.method == "POST":
        role = request.POST.get("role")
        mobile = request.POST.get("mobile")

        print(role)     # customer or business
        print(mobile)
        # user_id = request.POST.get("mobile")
        # data = token()
        # print(data)
        request.session["mobile"] = mobile
        request.session["role"] = role
        # request.session["token"] = data["token"]
        

        # Send OTP
        # response = send_phone_otp(mobile, data["token"])
        # response_data = response.get("data", {})

        # if response.get("responseCode") in [200, 506]:
        #     request.session["verificationId"] = response_data.get("verificationId")
        #     logger.info(f"OTP sent successfully to {mobile}")
        return redirect(f"/loyalty/loyalty-otp-verification")
        

        message = "Retry sending OTP"
        logger.warning(f"Failed OTP attempt for {mobile}: {response}")

    return render(request, "Loyalty/Business_SIde/Landing.html")


def send_otp(request):

    if request.method != "POST":
        return JsonResponse({"status": False}, status=405)

    mobile = request.session.get("mobile")

    if not mobile:
        return JsonResponse(
            {
                "status": False,
                "message": "Session expired"
            },
            status=400
        )

    try:

        data = token()
        print(data["token"])

        request.session["token"] = data["token"]

        response = send_phone_otp(
            mobile,
            data["token"]
        )

        if response.get("responseCode") in [200, 506]:

            request.session["verificationId"] = response["data"]["verificationId"]
            print("otp request sent")

            return JsonResponse(
                {
                    "status": True,
                    "message": "OTP Sent"
                }
            )

        return JsonResponse(
            {
                "status": False,
                "message": "Unable to send OTP"
            }
        )

    except Exception as e:

        logger.exception(e)

        return JsonResponse(
            {
                "status": False,
                "message": "Something went wrong"
            }
        )

def otp_verification(request):
    """
    Handles OTP verification.
    """

    message = ""
    business_hash_id = request.session.get("business_hash_id")
    print("business_hash",business_hash_id)
    # Session values
    user_id = request.session.get("mobile")           # mobile number
    token = request.session.get("token")
    verification_id = request.session.get("verificationId")
    role = request.session.get("role")   

    if request.method == "POST":

        otp1 = request.POST.get("otp1", "")
        otp2 = request.POST.get("otp2", "")
        otp3 = request.POST.get("otp3", "")
        otp4 = request.POST.get("otp4", "")

        otp = otp1 + otp2 + otp3 + otp4

        if len(otp) != 4:
            return JsonResponse({"error": "Invalid OTP"}, status=400)

                      # customer/business

        if not user_id or not token or not verification_id:
            return render(
                request,
                "photo_frame/client_error.html",
                {
                    "error_message":
                    "Session expired. Please restart the process."
                }
            )

        response = verify_otp(
            user_id,
            otp,
            verification_id,
            token
        )

        if response.get("responseCode") == 200:

            # -----------------------------------------
            # USER EXISTS?
            # -----------------------------------------
            try:
                user = User.objects.get(username=user_id)
                created = False
            except User.DoesNotExist:
                created = True

                user = User.objects.create_user(
                    username=user_id,
                    password=None
                )
                # if business_hash_id == None and role == "customer":
                #     messages.error(request, "Invalid access. Please scan the QR code again.")
                #     return redirect("/loyalty/signin/")

                if role == "business":
                    group = Group.objects.get(name="LOYALTY-BUSINESS")
                else:
                    group = Group.objects.get(name="LOYALTY-CUSTOMER")

                user.groups.add(group)

            # Login user
            login(request, user)
            print(request.user)

            # -----------------------------------------
            # Existing User
            # -----------------------------------------
            if not created:

                if user.groups.filter(name="LOYALTY-BUSINESS").exists():
                    return redirect("/loyalty/business-dashboard")

                elif user.groups.filter(name="LOYALTY-CUSTOMER").exists():
                    return redirect(
                        f"/loyalty/customer-scanned-success/{business_hash_id}"
                    )

            # -----------------------------------------
            # Newly Created User
            # -----------------------------------------
            else:

                if role == "business":
                    return redirect("/loyalty/business-welcome")

                else:
                    return redirect(
                        f"/loyalty/customer-name/{business_hash_id}",
                    )

        message = "Wrong OTP. Please enter the correct OTP."

    return render(
        request,
        "Loyalty/Business_SIde/OTP_Verification.html",context=
        {
            "message": message,
            "mobile":user_id,
        }
    )


def validate_avaibality(request):
    business_user = request.user
    business_user_profile = BusinessProfile.objects.filter(user=business_user).first()
    is_available=business_user_profile.active

    return is_available

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_business, login_url="/loyalty/signin")
def welcome_business(request):
    """
    Create/Update Business Profile
    """
    print("business profile")

    # Only business users are allowed
    if not request.user.groups.filter(name="LOYALTY-BUSINESS").exists():
        messages.error(request, "You are not authorized to access this page.")
        return redirect("/loyalty/signin/")

    if request.method == "POST":
        print("post method")

        name = request.POST.get("name", "").strip()
        business_name = request.POST.get("businessName", "").strip()
        business_category = request.POST.get("category", "").strip()
        business_contact = request.POST.get("phone", "").strip()
        latitude = request.POST.get("latitude", "").strip()
        longitude = request.POST.get("longitude", "").strip()

        # -----------------------
        # Validation
        # -----------------------

        if not name:
            messages.error(request, "Please enter your name.")
            return render(
                request,
                "Loyalty/Business_SIde/Welcome_Business.html"
            )

        if not business_name:
            messages.error(request, "Please enter business name.")
            return render(
                request,
                "Loyalty/Business_SIde/Welcome_Business.html"
            )

        if not latitude or not longitude:
            messages.error(request, "Please pin your business location.")
            return render(
                request,
                "Loyalty/Business_SIde/Welcome_Business.html"
            )

        # Optional phone validation
        if business_contact:
            if (
                len(business_contact) != 10
                or not business_contact.isdigit()
                or business_contact[0] not in "6789"
            ):
                messages.error(request, "Enter a valid mobile number.")
                return render(
                    request,
                    "Loyalty/Business_SIde/Welcome_Business.html"
                )

        try:

            # Check existing profile
            profile = BusinessProfile.objects.filter(
                user=request.user
            ).first()

            if profile is None:
                print("profile not found")

                # Create new profile
                BusinessProfile.objects.create(
                    user=request.user,
                    business_partner_name=name,
                    business_name=business_name,
                    business_category=business_category,
                    business_contact=business_contact,
                    latitude=latitude,
                    longitude=longitude,
                )

                messages.success(
                    request,
                    "Business profile created successfully."
                )

            else:
                print("profile found")

                # Update existing profile
                profile.name = name
                profile.business_name = business_name
                profile.business_category = business_category
                profile.business_contact = business_contact
                profile.latitude = latitude
                profile.longitude = longitude

                profile.save()

                messages.success(
                    request,
                    "Business profile updated successfully."
                )

            return redirect("/loyalty/business-dashboard")

        except IntegrityError as e:

            logger.exception(e)

            messages.error(
                request,
                "Unable to save profile. Please try again."
            )

        except Exception as e:

            logger.exception(e)

            messages.error(
                request,
                "Something went wrong. Please try again."
            )


    return render(request, "Loyalty/Business_SIde/Welcome_Business.html")

from django.utils import timezone

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_business, login_url="/loyalty/signin")
def business_dashboard(request):
    """
    Displays the business dashboard for business users.
    """  
    # userid_hash = encode_primary_key(hashid)
    try:
        is_available = validate_avaibality(request)
        business_user = request.user
        business_user_profile = BusinessProfile.objects.filter(user=business_user).first()
        if is_available:
            
            business_customers = CustomerVisitCount.objects.filter(business=business_user_profile).count()
            approval_awating_customers = CustomerVisitHistory.objects.filter(customer_visit__business=business_user_profile, approval_status=False,action="EARNED").all()

            pending_scans = []
            
            total_scans = CustomerVisitHistory.objects.filter(customer_visit__business=business_user_profile, approval_status=True).count()
            total_redeemed_rewards = CustomerVisitHistory.objects.filter(customer_visit__business=business_user_profile, approval_status=True, action="REDEEMED").count()
            reward_programs = BusinessOffer.objects.filter(business=business_user_profile).all()

            ############# Timezone aware date filtering for today visits count#############
            today = timezone.localdate()
            start = timezone.make_aware(
                datetime.combine(today, time.min)
            )
            end = start + timedelta(days=1)
            today_visit_count = CustomerVisitHistory.objects.filter(
                customer_visit__business=business_user_profile,
                created_at__gte=start,
                created_at__lt=end,
                approval_status=True
            ).count()

            today_redeemed_count = CustomerVisitHistory.objects.filter(
                        customer_visit__business=business_user_profile,
                        created_at__gte=start,
                        created_at__lt=end,
                        approval_status=True,
                        action="REDEEMED"
                    ).count()

            for visit in approval_awating_customers:
                pending_scans.append({
                    "id": visit.id,
                    "name": visit.customer_visit.customer.name,
                    "phone": visit.customer_visit.customer.contact,
                    "time": visit.created_at.isoformat(),
                })
            ##################### get weekly visits count for the last 7 days #####################
            weekly_visits = []

            today = timezone.localdate()

            for i in range(6, -1, -1):

                day = today - timedelta(days=i)

                start = timezone.make_aware(
                    datetime.combine(day, time.min)
                )

                end = start + timedelta(days=1)

                count = CustomerVisitHistory.objects.filter(
                    customer_visit__business=business_user_profile,
                    approval_status=True,
                    created_at__gte=start,
                    created_at__lt=end,
                ).count()

                weekly_visits.append(count)

            #####################daily added customers count for the last 7 days#####################
            weekly_new_customers = []

            today = timezone.localdate()

            for i in range(6, -1, -1):

                day = today - timedelta(days=i)

                start = timezone.make_aware(
                    datetime.combine(day, time.min)
                )

                end = start + timedelta(days=1)

                count = CustomerVisitCount.objects.filter(
                    business=business_user_profile,
                    created_at__gte=start,
                    created_at__lt=end,
                ).count()

                weekly_new_customers.append(count)

            ########################### return the context to the template #########################
            return render(request, "Loyalty/Business_SIde/Home.html", context={
                "business_user_profile": business_user_profile,
                "business_customers": business_customers,
                "pending_scans": json.dumps(pending_scans),
                "total_scans": total_scans,
                "total_redeemed_rewards": total_redeemed_rewards,
                "today_visit_count": today_visit_count,
                "today_redeemed_count": today_redeemed_count,
                "reward_programs": reward_programs,
                "weekly_visits": json.dumps(weekly_visits),
                "weekly_new_customers": json.dumps(weekly_new_customers),
                "customer_url":f"https://www.aliveframe.com/loyalty/customer-scanned-success/{encode_primary_key(business_user_profile.id)}",
                "premium_status": "Premium" ,
            })
        # "customer_url":f"https://55b2-2401-4900-7031-f46f-508-1856-de34-abb8.ngrok-free.app/loyalty/customer-scanned-success/{encode_primary_key(business_user_profile.id)}",
         # "customer_url":f"https://www.aliveframe.com/loyalty/customer-scanned-success/{encode_primary_key(business_user_profile.id)}",
    # f"https://2b94-2401-4900-d154-e28f-c6d-4398-1b79-4a1.ngrok-free.app/loyalty/customer-scanned-success/{encode_primary_key(business_user_profile.id)}"
        else:
            pending_scans=[]
            weekly_visits=[]
            weekly_new_customers=[] 
            ########################### return the context to the template #########################
            return render(request, "Loyalty/Business_SIde/Home.html", context={
                "business_user_profile": business_user_profile,
                "business_customers": 0,
                "pending_scans": json.dumps(pending_scans),
                "total_scans": 0,
                "total_redeemed_rewards": 0,
                "today_visit_count": 0,
                "today_redeemed_count": 0,
                "reward_programs": 0,
                "weekly_visits": json.dumps(weekly_visits),
                "weekly_new_customers": json.dumps(weekly_new_customers),
                "customer_url":f"https://www.aliveframe.com/loyalty/customer-scanned-success/{encode_primary_key(business_user_profile.id)}",
                "premium_status": "Free",
            })

    except Exception as e:
        logger.exception("Error while loading AR games page")
        return render(request, "client_error.html", {
            "error_message": "An unexpected error occurred. Please try again later."
        })


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from .models import CustomerVisitHistory, BusinessProfile


@login_required(login_url="/loyalty/signin")
@user_passes_test(is_business, login_url="/loyalty/signin")
@require_POST
def approve_visit(request, visit_id):

    visit = get_object_or_404(
        CustomerVisitHistory,
        id=visit_id,
    )

    # Prevent approving the same visit twice
    if visit.approval_status:
        return JsonResponse({
            "success": False,
            "message": "Visit has already been approved."
        }, status=400)

    # Approve visit
    visit.approval_status = True
    visit.save(update_fields=["approval_status"])

    # Increment visit count atomically
    CustomerVisitCount.objects.filter(
        id=visit.customer_visit_id
    ).update(
        visits_count=F("visits_count") + 1,
        total_visits=F("total_visits") + 1
    )

    return JsonResponse({
        "success": True,
        "message": "Visit approved successfully."
    })


@login_required(login_url="/loyalty/signin")
@user_passes_test(is_business, login_url="/loyalty/signin")
@require_POST
def reject_visit(request, visit_id):
    visit = get_object_or_404(
        CustomerVisitHistory,
        id=visit_id)

    visit.delete()

    return JsonResponse({
        "success": True,
        "message": "Visit rejected successfully."
    })

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_business, login_url="/loyalty/signin")
def business_profile(request):
    """
    Display Business Profile Page
    """
    business_user = request.user
    
    # business_user=User.objects.filter(username=9631218850).first()
    
    profile = BusinessProfile.objects.filter(user=business_user).first()

    context = {
        "profile": profile
    }

    return render(
        request,
        "Loyalty/Business_SIde/Profile.html",
        context
    )


@login_required(login_url="/loyalty/signin")
@user_passes_test(is_business, login_url="/loyalty/signin")
@require_POST
def update_business_profile(request):

    # profile = BusinessProfile.objects.get(user=request.user)
    business_user = request.user
    # business_user_id = decode_primary_key(hashid)
    # argame = ArGame.objects.filter(id=userid).first()
    # staff = BusinessProfile.objects.filter(user=business_user).first()
    # business_user=User.objects.filter(username=9631218850).first()
    profile = BusinessProfile.objects.filter(user=business_user).first()

    data = json.loads(request.body)
    print(data)

    profile.business_partner_name = data.get(
        "business_partner_name",
        profile.business_partner_name
    )

    profile.business_name = data.get(
        "business_name",
        profile.business_name
    )

    profile.business_category = data.get(
        "business_category",
        profile.business_category
    )

    profile.address = data.get(
        "address",
        profile.address
    )

    profile.business_contact = data.get(
        "business_contact",
        profile.business_contact
    )

    profile.email = data.get(
        "email",
        profile.email
    )

    profile.instagram_url = data.get(
        "instagram_url",
        profile.instagram_url
    )

    profile.facebook_url = data.get(
        "facebook_url",
        profile.facebook_url
    )

    profile.youtube_url = data.get(
        "youtube_url",
        profile.youtube_url
    )

    profile.google_review_url = data.get(
        "google_review_url",
        profile.google_review_url
    )

    profile.open_at = data.get(
        "open_at",
        profile.open_at
    )

    profile.close_at = data.get(
        "close_at",
        profile.close_at
    )

    profile.latitude = data.get(
        "latitude",
        profile.latitude
    )

    profile.longitude = data.get(
        "longitude",
        profile.longitude
    )
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    profile.latitude = Decimal(latitude) if latitude else None
    profile.longitude = Decimal(longitude) if longitude else None

    profile.save()

    return JsonResponse({
        "success": True,
        "message": "Profile Updated Successfully"
    })

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_business, login_url="/loyalty/signin")
def create_offer(request):
    """
    Handles offer creation for business users.
    """
    business_user = request.user
    
    business_user_profile = BusinessProfile.objects.filter(user=business_user).first()



    return render(request, "Loyalty/Business_SIde/Create_Offer.html",context={"business_user_profile":business_user_profile})

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_business, login_url="/loyalty/signin")
def create_stamp_card(request):
    """
    Handles stamp card creation for business users.
    """
    business_user = request.user
    # business_user_id = decode_primary_key(hashid)
    # argame = ArGame.objects.filter(id=userid).first()
    # staff = BusinessProfile.objects.filter(user=business_user).first()
    # business_user=User.objects.filter(username=9631218850).first()
    
    business_user_profile = BusinessProfile.objects.filter(user=business_user).first()
    business_offer = BusinessOffer.objects.filter(business=business_user_profile).all()

    offer_list = []

    for off in business_offer:
        offer_list.append({
            "id": off.id,
            "image": off.offer_image.url if off.offer_image else None,
            "visits": off.visit_required if off.visit_required is not None else 0,
            "expiryDays": off.reward_expiration_days if off.reward_expiration_days is not None else 30,
            "description": off.offer_details or "",
        })
    print(offer_list)

    

    # { id: 1, image: null, visits: 2, expiryDays: 30, description: "After two Sattu one will be free" },

    return render(request, "Loyalty/Business_SIde/Create_Stamp.html", context={
        "offer_list":json.dumps(offer_list),
        "business_name": business_user_profile.business_name
    })

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_business, login_url="/loyalty/signin")
def customers_list(request):
    """
    Displays customers for the logged-in business with
    search and pagination.
    """

    try:
        business = BusinessProfile.objects.get(user=request.user)
        business_user_profile = business
    except BusinessProfile.DoesNotExist:
        return redirect("/loyalty/business-welcome")

    customer_visits = (
        CustomerVisitCount.objects
        .filter(business=business)
        .select_related("customer")
        .prefetch_related(
            Prefetch(
                "visit_history",
                queryset=CustomerVisitHistory.objects.select_related("offer").order_by("-created_at")
            )
        )
        .order_by("-created_at")
    )

    customers = []

    for visit in customer_visits:

        history = list(visit.visit_history.all())

        # Latest scan
        last_visit = history[0].created_at.isoformat() if history else None

        # All scan timestamps
        scans = [
            h.created_at.isoformat()
            for h in history
            if h.action == "EARNED"
        ]

        # Stamp rewards
        stamp_rewards = []
        stamp_rewards_earned = 0
        stamp_rewards_redeemed = 0

        # Scratch cards (future support)
        scratch_cards = []
        scratch_played = 0
        scratch_won = 0

        for h in history:

            if h.action == "EARNED":

                stamp_rewards_earned += 1

                if h.approval_status:
                    status = "approved"
                else:
                    status = "awaiting"

                stamp_rewards.append({
                    "name": h.offer.offer_details if h.offer else "Reward",
                    "stamps": visit.visits_count,
                    "earnedAt": h.created_at.isoformat(),
                    "status": status,
                })

            elif h.action == "REDEEMED":

                stamp_rewards_redeemed += 1

                stamp_rewards.append({
                    "name": h.offer.offer_details if h.offer else "Reward",
                    "stamps": visit.visits_count,
                    "earnedAt": h.created_at.isoformat(),
                    "status": "redeemed",
                })

        customers.append({
            "id": visit.customer.id,
            "name": visit.customer.name,
            "phone": visit.customer.contact,
            "email": visit.customer.email,
            "profileImage": visit.customer.profile_image.url if visit.customer.profile_image else None,

            # Current stamp progress
            "stamps": visit.visits_count,
            "total": visit.total_visits,

            # Total visits made
            "visits": len(scans),

            # Latest visit
            "lastVisit": last_visit,

            # Reward statistics
            "stampRewardsEarned": stamp_rewards_earned,
            "stampRewardsRedeemed": stamp_rewards_redeemed,

            # Scratch card statistics
            "scratchPlayed": scratch_played,
            "scratchWon": scratch_won,

            # Reward details
            "stampRewards": stamp_rewards,

            # Scratch cards
            "scratchCards": scratch_cards,

            # Visit history
            "scans": scans,
        })

    return render(
        request,
        "Loyalty/Business_SIde/Customers.html",
        {"business_user_profile":business_user_profile,
        "customers": json.dumps(customers),
        "business": business,
        },
    )

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_business, login_url="/loyalty/signin")
def winners_list(request):
    """
    Displays the list of winners for business users.
    """
    business_user = request.user
    # business_user_id = decode_primary_key(hashid)
    # argame = ArGame.objects.filter(id=userid).first()
    # staff = BusinessProfile.objects.filter(user=business_user).first()
    # business_user=User.objects.filter(username=9631218850).first()
    business_user_profile = BusinessProfile.objects.filter(user=business_user).first()
    business_customers = CustomerVisitCount.objects.filter(business=business_user_profile).count()
    approval_awating_customers = CustomerVisitHistory.objects.filter(customer_visit__business=business_user_profile,action="REDEEMED").all() 
    approval_awating_customers_list = []
    for visit in approval_awating_customers:
        if visit.approval_status == False:
            approval_awating_customers_list.append({
            "id": visit.id, "name": visit.customer_visit.customer.name, "phone": visit.customer_visit.customer.contact, "time": visit.created_at.isoformat(),
            "milestone": visit.offer.offer_details, "reward": visit.offer.offer_details,
            "claimedAt": visit.created_at.isoformat() if visit.created_at else None, "redeemedAt": None, "status": "pending",
            })

        elif visit.approval_status == True:
            approval_awating_customers_list.append({
            "id": visit.id, "name": visit.customer_visit.customer.name, "phone": visit.customer_visit.customer.contact, "time": visit.created_at.isoformat(),
            "milestone": visit.offer.offer_details, "reward": visit.offer.offer_details,
            "claimedAt": visit.created_at.isoformat() if visit.created_at else None, "redeemedAt": None, "status": "redeemed",
            })
    print("approval_awating_customers_list",approval_awating_customers_list)
    


    return render(request, "Loyalty/Business_SIde/Winners.html",context={
        "approval_awating_customers": json.dumps(approval_awating_customers_list),
        "business_user_profile_name":business_user_profile.business_name

    })

from django.db import transaction

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_business, login_url="/loyalty/signin")
@require_POST
@transaction.atomic
def accept_claim(request, visit_id):
    visit = get_object_or_404(
        CustomerVisitHistory,
        id=visit_id
    )

    if visit.approval_status:
        return JsonResponse({
            "success": False,
            "message": "This claim has already been approved."
        })

    if visit.offer is None:
        return JsonResponse({
            "success": False,
            "message": "Offer not found."
        })

    customer_visit = visit.customer_visit

    if customer_visit.visits_count < visit.offer.visit_required:
        return JsonResponse({
            "success": False,
            "message": "Not enough stamps."
        })

    # Approve reward request
    visit.approval_status = True
    visit.save(update_fields=["approval_status"])

    # Deduct stamps
    customer_visit.visits_count -= visit.offer.visit_required

    # Find remaining approved earned stamps
    earned_stamps = list(
    CustomerVisitHistory.objects.filter(
        customer_visit=customer_visit,
        action="EARNED",
        approval_status=True
    ).order_by("-created_at")
    )

    remaining_earned = earned_stamps[:customer_visit.visits_count]

    if remaining_earned:
        # Since the list is newest -> oldest,
        # the last element is the oldest remaining earned stamp.
        customer_visit.active_offer_last_visit = remaining_earned[-1].created_at
    else:
        customer_visit.active_offer_last_visit = timezone.now()

    customer_visit.save(update_fields=[
        "visits_count",
        "active_offer_last_visit"
    ])

    return JsonResponse({
        "success": True,
        "message": "Claim accepted successfully."
    })

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_business, login_url="/loyalty/signin")
@require_POST
def reject_claim(request, visit_id):
    visit = get_object_or_404(
        CustomerVisitHistory,
        id=visit_id)

    visit.delete()

    return JsonResponse({
        "success": True,
        "message": "Claim rejected successfully."
    })

import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_business, login_url="/loyalty/signin")
@require_POST
def save_rewards(request):

    business_user = request.user
        # business_user_id = decode_primary_key(hashid)
        # argame = ArGame.objects.filter(id=userid).first()
        # staff = BusinessProfile.objects.filter(user=business_user).first()
    # business_user=User.objects.filter(username=9631218850).first()

    business = get_object_or_404(
        BusinessProfile,
        user=business_user
    )

    try:
        body = json.loads(request.body)
        print(body)
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "message": "Invalid request."
        })

    rewards = body.get("rewards", [])

    # Existing reward ids in database
    existing_ids = set(
        BusinessOffer.objects.filter(
            business=business
        ).values_list("id", flat=True)
    )

    received_ids = set()

    for reward in rewards:

        reward_id = reward.get("id")

        # ---------------- UPDATE ----------------
        if reward_id and str(reward_id).isdigit():
            print("reward update")

            offer = BusinessOffer.objects.filter(
                id=reward_id,
                business=business
            ).first()

            if offer:

                offer.offer_details = reward.get("description", "")
                offer.visit_required = reward.get("visits", 0)
                offer.reward_expiration_days = reward.get("expiryDays", 30)
                offer.available = True

                offer.save()

                received_ids.add(offer.id)

        # ---------------- CREATE ----------------
        else:
            print("reward created")

            offer = BusinessOffer.objects.create(
                business=business,
                offer_details=reward.get("description", ""),
                visit_required=reward.get("visits", 0),
                reward_expiration_days=reward.get("expiryDays", 30),
                available=True
            )

            received_ids.add(offer.id)

    # ---------------- DELETE REMOVED REWARDS ----------------
    delete_ids = existing_ids - received_ids

    if delete_ids:
        BusinessOffer.objects.filter(
            business=business,
            id__in=delete_ids
        ).delete()

    return JsonResponse({
        "success": True,
        "message": "Reward programs saved successfully."
    })

    
def business_help(request):
    """
    Displays the help page for business users.
    """

    return render(request, "Loyalty/Business_SIde/Help&Support.html")


@login_required
@require_POST
def update_avaibality(request):
    is_available=False

    return is_available

def activate_business(user):
    """
    Activate the business after successful payment.
    """

    business = get_object_or_404(
        BusinessProfile,
        user=user
    )

    business.active = True
    business.save(update_fields=["active"])

    return business

def payment(request):
    """
    Displays the payment history for business users.
    """
    business_user = request.user

    return render(request, "Loyalty/Business_SIde/PaymentPage.html",context={"business_user":business_user.username})

@login_required
@require_POST
def create_order(request):
    business_user = request.user
    business = BusinessProfile.objects.get(user=request.user)
    print(business)

    data = json.loads(request.body)

    plan = data.get("plan")
    print("plan",plan)

    plans =  {"Starter": 1,
            "Pro": 2,
            "Advance": 3,
            "Enterprise": 4,}
    
    # {

    #     "starter": 99900,
    #     "growth": 189900,
    #     "pro": 269900,
    #     "advance": 429900,

    # }


    if plan not in plans:

        return JsonResponse({
            "success": False,
            "message": "Invalid Plan"
        })

    amount = plans[plan] * 100

    order = client.order.create({

        "amount": amount,

        "currency": "INR",

        "payment_capture": 1

    })


    SubscriptionPayment.objects.create(

        user=request.user,

        razorpay_order_id=order["id"],

        plan=plan,

        amount=amount

    )

    return JsonResponse({

        "success": True,

        "order_id": order["id"],

        "amount": amount,

        "currency": "INR",

        "key": settings.RAZOR_KEY_ID,

        "name": business.business_name,
        "email": business.email or "",
        "phone": business.business_contact or "",

    })

@login_required
@require_POST
def verify_payment(request):

    data = json.loads(request.body)

    order_id = data.get("razorpay_order_id")

    payment_id = data.get("razorpay_payment_id")

    signature = data.get("razorpay_signature")

    try:
        print("payment success")

        client.utility.verify_payment_signature({

            "razorpay_order_id": order_id,

            "razorpay_payment_id": payment_id,

            "razorpay_signature": signature

        })

    except Exception:
        print("verification failed")

        return JsonResponse({

            "success": False,

            "message": "Signature verification failed"

        })

    payment = SubscriptionPayment.objects.filter(

        razorpay_order_id=order_id,

        user=request.user

    ).first()
    print(payment)

    if payment is None:

        return JsonResponse({

            "success": False,

            "message": "Order not found"

        })

    if payment.status == "SUCCESS":
        print("pay success")

        return JsonResponse({

            "success": True,

            "message": "Already Verified"

        })

    if payment.amount <= 0:

        return JsonResponse({

            "success": False,

            "message": "Invalid Amount"

        })

    payment.razorpay_payment_id = payment_id

    payment.razorpay_signature = signature

    payment.status = "SUCCESS"

    payment.verified_at = timezone.now()

    payment.save()

    # --------------------------------------
    # ACTIVATE SUBSCRIPTION HERE
    # --------------------------------------
    #
    business = BusinessProfile.objects.get(user=request.user)
    
    business.subscription_plan = payment.plan
    
    business.subscription_expiry = timezone.now() + timedelta(days=365)
    
    business.active = True
    
    business.save()
    #
    # --------------------------------------

    return JsonResponse({

        "success": True,

        "message": "Payment Verified"

    })

def business_privacy_policy(request):
    """
    Displays the privacy policy for business users.
    """

    return render(request, "Loyalty/Business_SIde/Privacy&Security.html")


################################################################################################
############################Customer Side Views########################################################
################################################################################################

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_customer, login_url="/loyalty/signin")
def customer_name(request, hash_id):
    """
    Save customer name and redirect to customer dashboard.
    """

    customer, created = CustomerProfile.objects.get_or_create(
    user=request.user,
     defaults={
        "name": "",
        "contact":request.user.username
    }
    )

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        print(name)

        if name:
            customer.name = name
            customer.save(update_fields=["name"])

            return redirect(
                f"/loyalty/customer-scanned-success/{hash_id}"
            )

    return render(
        request,
        f"Loyalty/Customer_Side/customer_name.html"
    )

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_customer, login_url="/loyalty/signin")
def customer_dashboard(request, hash_id):
    """
    Displays the customer dashboard for customers.
    """
    business_offers = BusinessOffer.objects.filter(business__id=decode_primary_key(hash_id)).all()
    # customer_user=User.objects.filter(username=7319847865).first()
    customer_user = request.user
    print(customer_user)
    customer_profile = CustomerProfile.objects.filter(user=customer_user).first()
   
    # customer_visit_count = CustomerVisitCount.objects.filter(customer=customer_profile, business__id=decode_primary_key(hash_id)).first()
    customer_visit_count = CustomerVisitCount.objects.filter(customer=customer_profile, business__id=decode_primary_key(hash_id)).first()

    
    redeemed_count = CustomerVisitHistory.objects.filter(
                    customer_visit=customer_visit_count,
                    action="REDEEMED",
                    approval_status=True
                        ).count()
    total_visits = CustomerVisitHistory.objects.filter(
                    customer_visit=customer_visit_count,
                    approval_status=True
                        ).count()
    active_visits = customer_visit_count.visits_count if customer_visit_count else 0
    rewards = []

    for offer in business_offers:
        rewards.append({
            "id": str(offer.id),
            "business": offer.business.business_name,
            "logo": offer.offer_image.url if offer.offer_image else None,
            "offer": offer.offer_details,
            "stamps": customer_visit_count.visits_count,  # Replace if you want customer's earned stamps
            "goal": offer.visit_required,
        })

    

    print("rewards", rewards)

    
    return render(request, "Loyalty/Customer_Side/Customer_Home.html", context={
        "customer_profile": customer_profile,
        "business_offers": business_offers,
        "rewards": json.dumps(rewards),
        "redeemed_count": redeemed_count,
        "total_visits": total_visits,
        "active_visits": active_visits,
        "hash_id": hash_id,
    })

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_customer, login_url="/loyalty/signin")
def customer_profile(request, hash_id):
    """
    Displays the customer profile for customers.
    """
    customer_user = request.user
    
    # business_user=User.objects.filter(username=9631218850).first()
    
    profile = CustomerProfile.objects.filter(user=customer_user).first()
    print(profile.name)


    return render(request, "Loyalty/Customer_Side/My_Profile.html", context={
        "hash_id": hash_id,
        "profile": profile,
    })

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_customer, login_url="/loyalty/signin")
def customer_rewards(request, hash_id):
    """
    Displays the customer rewards for customers.
    """

    customer = CustomerProfile.objects.get(user=request.user)
    print(customer)

    rewards = []

    customer_visits = (
        CustomerVisitCount.objects
        .select_related("business")
        .filter(customer=customer)
    )
    print(customer_visits)

    for visit in customer_visits:
        reward_hashed_id = encode_primary_key(visit.id)

        offers = (
            BusinessOffer.objects
            .filter(
                business=visit.business,
                available=True
            )
            .order_by("visit_required")
        )

        for offer in offers:

            # Customer has earned this reward
            if visit.visits_count >= offer.visit_required:

                expiry_date = (
                    visit.active_offer_last_visit +
                    timedelta(days=offer.reward_expiration_days)
                )

                # Optional: Skip expired rewards
                if timezone.now() > expiry_date:
                    status = "expired"
                else:
                    status = "ready"

                rewards.append({
                    "customer_hashed_id": reward_hashed_id,
                    "id":str(offer.id),
                    "business": visit.business.business_name,
                    "title": offer.offer_details,
                    "group": None,
                    "status": status,
                    "expires": expiry_date.strftime("%d/%m/%Y"),
                })

    history = (
        CustomerVisitHistory.objects
        .select_related("customer_visit__business")
        .filter(
            customer_visit__customer=customer,
            action="REDEEMED",
            approval_status=True
        )
        .order_by("-created_at")
    )

    history_list = []

    for item in history:
        history_list.append({
            "business": item.customer_visit.business.business_name,
            "date": item.created_at.strftime("%b %d, %Y"),
            "status": "redeemed"
        })

    print(history_list)

    return render(
        request,
        "Loyalty/Customer_Side/My_Rewards.html",
        {
            "hash_id": hash_id,
            "rewards": json.dumps(rewards),
            "history": json.dumps(history_list),
        },)

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_customer, login_url="/loyalty/signin")
def customer_explore(request, hash_id):
    """
    Displays the customer explore page for customers.
    """
    businesses = (
        BusinessProfile.objects
        .filter(active=True)
        .order_by("business_name")
    )

    # Get unique categories
    categories = ["All"]
    categories.extend(
        BusinessProfile.objects
        .filter(active=True)
        .values_list("business_category", flat=True)
        .distinct()
        .order_by("business_category")
    )

    # Get business list
    business_list = []

    for business in businesses:
        business_hash_id = encode_primary_key(business.id)
        business_list.append([
            business.business_name,
            business.business_category,
            business_hash_id
        ])
    print(categories)
    print(business_list)

    return render(request, "Loyalty/Customer_Side/Explore.html", context={
        "hash_id": hash_id,
        "categories": json.dumps(categories),
        "businesses": json.dumps(business_list),
    })

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_customer, login_url="/loyalty/signin")
def customer_scanner(request, hash_id):
    """
    Displays the customer scanner page for customers.
    """

    return render(request, "Loyalty/Customer_Side/Scan.html", context={
        "hash_id": hash_id
    })


@login_required(login_url="/loyalty/signin")
@user_passes_test(is_customer, login_url="/loyalty/signin")
def customer_scanned_success(request, hash_id):
    """
    Displays the scanned success page for customers.
    """
    print("VIEW REACHED")
    business_hash_id = request.session.get("business_hash_id")
    print(business_hash_id)

    customer = get_object_or_404(
        CustomerProfile,
        user=request.user
    )
    print("customer", customer)

    business = get_object_or_404(
        BusinessProfile,
        id=decode_primary_key(hash_id)
    )

    print("business", business)

    # Create visit count object if it doesn't exist
    customer_visit, created = CustomerVisitCount.objects.get_or_create(
        customer=customer,
        business=business,
        defaults={
            "visits_count": 0,
            "total_visits": 0
        }
    )
    print(customer_visit)

    # Check if an unapproved request already exists
    pending_visit = CustomerVisitHistory.objects.filter(
        customer_visit=customer_visit,
        approval_status=False
    ).exists()

    if not pending_visit:
        CustomerVisitHistory.objects.create(
            customer_visit=customer_visit,
            action="EARNED",
            approval_status=False
        )

    return render(
        request,
        "Loyalty/Customer_Side/ScannedSuccess.html",
        {
            "business_hash_id": hash_id,
            "pending_visit": pending_visit,
        }
    )

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_customer, login_url="/loyalty/signin")
def stamp_card_details(request, hash_id, reward_id):
    """
    Displays the stamp card details page for customers.
    """
    print(reward_id)
    # customer_user=User.objects.filter(username=7319847865).first()
    customer_user = request.user
    customer_profile = CustomerProfile.objects.filter(user=customer_user).first()
    business_id=int(decode_primary_key(hash_id))
    business_offers = BusinessOffer.objects.filter(business__id=business_id).all()
    business_profile = BusinessProfile.objects.filter(id=business_id).first()
    customer_visit_count = CustomerVisitCount.objects.filter(customer=customer_profile, business=business_profile).first()
    customer_visit_history = CustomerVisitHistory.objects.filter(customer_visit=customer_visit_count, approval_status=True, action="REDEEMED").all()
    customer_visit_history_unapproved = CustomerVisitHistory.objects.filter(customer_visit=customer_visit_count, approval_status=False).count()
    
    rewards = []

    for offer_item in business_offers:
            last_visit = timezone.localtime(customer_visit_count.active_offer_last_visit)
            today = timezone.localtime(timezone.now())
        
            days_left = max(
                0,
                offer_item.reward_expiration_days - (today - last_visit).days
            )
        
            print(days_left)
            rewards.append({
                "id": str(offer_item.id),
                "title": offer_item.offer_details,
                "image": offer_item.offer_image.url if offer_item.offer_image else None,
                "required": offer_item.visit_required,
                "claimed": False,
                "expiryDays": days_left,
            })


    
    for offer_item in customer_visit_history:
        last_visit = timezone.localtime(customer_visit_count.active_offer_last_visit)
        today = timezone.localtime(timezone.now())
    
        days_left = max(
            0,
            offer_item.offer.reward_expiration_days - (today - last_visit).days
        )
    
        print(days_left)
        rewards.append({
            "id": str(offer_item.offer.id),
            "title": offer_item.offer.offer_details,
            "image": offer_item.offer.offer_image.url if offer_item.offer.offer_image else None,
            "required": offer_item.offer.visit_required,
            "claimed": True if offer_item.action == "REDEEMED" else False,
            "expiryDays": days_left,
        })
        time=business_profile.open_at.strftime("%I:%M %p") if business_profile.open_at else ""
        print(time )
        print(encode_primary_key(customer_visit_count.id) if customer_visit_count else None)


    return render(request, "Loyalty/Customer_Side/stamp_detail_of_shop.html", context={
        "business_name": business_profile.business_name,
        "rewards": json.dumps(rewards),
        "hash_id": hash_id,
        "reward_id": reward_id,
        "customer_visit_hash_id": encode_primary_key(customer_visit_count.id) if customer_visit_count else None,
        "visit_count": customer_visit_count.visits_count if customer_visit_count else 0,
        "customer_visit_history_unapproved": customer_visit_history_unapproved,
        "open_at": business_profile.open_at.strftime("%I:%M") if business_profile.open_at else "",
        "close_at": business_profile.close_at.strftime("%I:%M") if business_profile.close_at else "",
        "business_address": business_profile.address if business_profile.address else "",
        "contact": business_profile.business_contact if business_profile.business_contact else "",
        "instagram": business_profile.instagram_url if business_profile.instagram_url else "",
        "email": business_profile.email if business_profile.email else "",
        "facebook": business_profile.facebook_url if business_profile.facebook_url else "",
        "youtube": business_profile.youtube_url if business_profile.youtube_url else "",
        "google_review": business_profile.google_review_url if business_profile.google_review_url else "",
    })

@login_required(login_url="/loyalty/signin")
@user_passes_test(is_customer, login_url="/loyalty/signin")
@require_POST
def reward_approval_request(request, customer_visit_hash_id):
    # customer_user=User.objects.filter(username=7319847865).first()
    customer_user = request.user
    customer = get_object_or_404(
        CustomerVisitCount,
        id=int(decode_primary_key(customer_visit_hash_id)),
        customer__user=customer_user
    )

    data = json.loads(request.body)
    offer_id = data.get("offer_id")
    print("offer_id", offer_id)

    if not offer_id:
        return JsonResponse({
            "success": False,
            "message": "Offer id is required."
        })

    offer = get_object_or_404(
        BusinessOffer,
        id=offer_id,
        available=True
    )

    # Check if another request is already pending
    if CustomerVisitHistory.objects.filter(
        customer_visit=customer,
        offer=offer,
        action="REDEEMED",
        approval_status=False
    ).exists():

        return JsonResponse({
            "success": False,
            "message": "Reward request already pending approval."
        })

    # Check customer has enough stamps
    if customer.visits_count < offer.visit_required:
        return JsonResponse({
            "success": False,
            "message": "Not enough stamps to claim this reward."
        })

    CustomerVisitHistory.objects.create(
        customer_visit=customer,
        offer=offer,
        action="REDEEMED",
        approval_status=False
    )

    return JsonResponse({
        "success": True,
        "message": "Reward request sent successfully."
    })
