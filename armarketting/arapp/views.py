from django.contrib.auth import login, authenticate, logout
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render,redirect
from django.conf import settings
from arapp.models import *
from photo_frame.models import *
from .utils import *
import qrcode
import os
from django.http import HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib.auth import logout
from django.shortcuts import redirect
import logging
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import uuid
import json
from django.utils import timezone
from django.contrib.auth.models import User, Group
from django.utils.timezone import now
from django.db.models import F
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from collections import OrderedDict

# Configure logging
logger = logging.getLogger(__name__)


def is_staff(user):
    return user.groups.filter(name='STAFF').exists()

def is_client(user):
    return user.groups.filter(name='CLIENT').exists()

def staff_signin(request):
    """
    Handles client sign-in.
    """
    message = ''
    
    if request.method == "POST":
        try:
            # Extract user input
            mobile = request.POST.get("mobile", "").strip()
            password = request.POST.get("password", "").strip()

            # Validate mobile number (Assuming 10-digit format for India)
            if not mobile or not password:
                return render(request, "staff_signin.html", {
                    "message": "Mobile number and password are required."
                })
            
            if not mobile.isdigit() or len(mobile) != 10:
                return render(request, "staff_signin.html", {
                    "message": "Invalid mobile number. It should be a 10-digit number."
                })

            # Authenticate user
            user = authenticate(username=mobile, password=password)
            
            if user is not None:
                print("staff user")
                if is_staff(user):
                    print("staff user authenticated")
                    login(request, user)
                    print("staff user logged in",request.user.username)
                    logger.info("User %s logged in successfully.", user.username)
                    return redirect("/staff-dashboard")
                else:
                    return render(request, "staff_signin.html", {
                    "message": "Not authorized to access this page."
                })
            else:
                print("staff user not authenticated")
                logger.warning("Failed login attempt for mobile: %s", mobile)
                return render(request, "staff_signin.html", {
                    "message": "Invalid mobile number or password. Please try again or create an account."
                })
        
        except Exception as e:
            logger.exception("Error during client login: %s", str(e))
            return render(request, "client_error.html", {
                "message": "An unexpected error occurred. Please try again later."
            })

    return render(request, "staff_signin.html")

def staff_forget_id(request):
    """
    Handles client signup via phone number and OTP verification.
    """
    try:
        message = ""

        if request.method == "POST":
            user_id = request.POST.get("mobile")

            if not user_id:
                return JsonResponse({"error": "Mobile number is required"}, status=400)

            # Check if user already exists
            if not User.objects.filter(username=user_id).exists():
                message = "Mobile number not registered!"
                return render(request, "client_signup.html", {"message": message})

            # Generate OTP token
            data = token()
            request.session["user_id"] = user_id
            request.session["token"] = data["token"]

            # Send OTP
            response = send_phone_otp(user_id, data["token"])
            response_data = response.get("data", {})

            if response.get("responseCode") in [200, 506]:
                request.session["verificationId"] = response_data.get("verificationId")
                logger.info(f"OTP sent successfully to {user_id}")
                return redirect("/otp")

            message = "Retry sending OTP"
            logger.warning(f"Failed OTP attempt for {user_id}: {response}")

        return render(request, "client_signup_forget.html", {"message": message})

    except Exception as e:
        logger.exception("Error occurred during client signup")
        return render(request, "client_error.html", {"error_message": "An unexpected error occurred. Please try again later."})

def staff_otp_forget(request):
    """
    Handles OTP verification for user authentication.
    """
    try:
        message = ""

        if request.method == "POST":
            otp = request.POST.get("otp")

            # Validate OTP input
            if not otp:
                return JsonResponse({"error": "OTP is required"}, status=400)

            # Retrieve session data
            user_id = request.session.get("user_id")
            token = request.session.get("token")
            verification_id = request.session.get("verificationId")

            if not user_id or not token or not verification_id:
                logger.error("Session data missing for OTP verification")
                return render(request, "client_error.html", {"error_message": "Session expired. Please restart the process."})

            logger.info(f"Verifying OTP for user: {user_id}")

            # Verify OTP
            response = verify_otp(user_id, otp, verification_id, token)

            if response.get("responseCode") == 200:
                response_data = response.get("data", {})
                request.session["verificationStatus"] = response_data.get("verificationStatus")

                logger.info(f"OTP verified successfully for {user_id}")
                return redirect("/password")

            message = "Wrong OTP. Please enter the correct OTP."
            logger.warning(f"Incorrect OTP entered for {user_id}")

        return render(request, "client_forget_otp.html", {"message": message})

    except Exception as e:
        logger.exception("Error occurred during OTP verification")
        return render(request, "client_error.html", {"error_message": "An unexpected error occurred. Please try again later."})

def staff_signup_password_forget(request):
    """
    Handles client password setup after OTP verification.
    """
    try:
        if request.method == "POST":
            user_id = request.session.get("user_id")
            verification_status = request.session.get("verificationStatus")
            password = request.POST.get("password")

            # Validate session data
            if not user_id or verification_status != "VERIFICATION_COMPLETED":
                logger.warning("Session expired or invalid verification status for user: %s", user_id)
                return redirect("/forget-password")

            # Validate password
            if not password or len(password) < 6:
                logger.warning("Weak password attempt for user: %s", user_id)
                return render(request, "client_password.html", {"error": "Password must be at least 6 characters long."})

            # Check if user not already exists
            if not User.objects.filter(username=user_id).exists():
                logger.warning("User doesn't exists: %s", user_id)
                return render(request, "client_forget_password.html", {"error": "User not exists. Please signup instead."})

           # Check if user exists
            user, created = User.objects.get_or_create(username=user_id)

            # Update password (whether new or existing user)
            user.set_password(password)
            user.save()

            authenticated_user = authenticate(username=user_id, password=password)
            if authenticated_user is not None:
                login(request, authenticated_user)
                logger.info("User signed up and logged in: %s", user_id)
                return redirect("/dashboard")

            logger.error("User authentication failed after signup: %s", user_id)
            return render(request, "client_forget_password.html", {"error": "Account creation failed. Please try again."})

        return render(request, "client_forget_password.html")

    except Exception as e:
        logger.exception("Unexpected error in client_signup_password")
        return render(request, "client_error.html", {"error_message": "An error occurred. Please try again later."})

@login_required(login_url='/staff-signin')
@user_passes_test(is_staff)
def staff_dashboard(request):
    """
    Renders the user dashboard with client information, frame user details, 
    and frame usage statistics.
    """
    try:
        user = request.user
        logger.info(f"Accessing dashboard for user: {user.username} (ID: {user.id})")
        print(f"Accessing dashboard for user: {user.username} (ID: {user.id})")

        # Fetch client info
        staff = StaffProfile.objects.filter(user=user).first()
        print(staff)
        if not staff:
            logger.warning(f"No ClientInfo found for user: {user.username}")
            return JsonResponse({"error": "Client information not found."}, status=404)

        # Fetch frame user information
        client_list = ClientProfile.objects.all()
        context = {
            "client_list": client_list,
        }

        return render(request, "staff_dashboard.html", context)

    except Exception as e:
        logger.exception("Error occurred while loading user dashboard")
        return JsonResponse({"error": "An internal server error occurred."}, status=500)
    
@login_required(login_url='/staff-signin')
@user_passes_test(is_staff)
def frame_dashboard(request):
    """
    Renders the user dashboard with client information, frame user details, 
    and frame usage statistics.
    """
    try:
        user = request.user
        logger.info(f"Accessing dashboard for user: {user.username} (ID: {user.id})")
        print(f"Accessing dashboard for user: {user.username} (ID: {user.id})")

        # Fetch client info
        staff = StaffProfile.objects.filter(user=user).first()
        print(staff)
        if not staff:
            logger.warning(f"No ClientInfo found for user: {user.username}")
            return JsonResponse({"error": "Client information not found."}, status=404)

        # Fetch frame user information
        client_list = FrameUserInfo.objects.all().order_by('-date')

        context = {
            "client_list": client_list,
        }

        return render(request, "frame_dashboard.html", context)

    except Exception as e:
        logger.exception("Error occurred while loading user dashboard")
        return JsonResponse({"error": "An internal server error occurred."}, status=500)

def end_consumer_details(request, id):
    """
    Displays the details of a specific client.
    """
    try:
       

        # # Fetch the associated frame users
        frame_user = FrameUserInfo.objects.filter(id=id)

        logger.info(f"Accessing client details for Client ID: {id}")

        return render(
            request,
            "end_consumer_detail.html",
            context={
                
                "frame_user": frame_user
            }
        )

    except Exception as e:
        logger.exception("Error occurred while loading client details")
        return JsonResponse({"error": "An internal server error occurred."}, status=500)

@login_required(login_url='/staff-signin')
@user_passes_test(is_staff)
def staff_logout(request):
    """
    Handles user logout and redirects to the login page.
    """
    try:
        logout(request)
        logger.info("User logged out successfully.")
        return redirect("/staff-signin")
    except Exception as e:
        logger.exception("Error during logout: %s", str(e))
        return render(request, "client_error.html", {
            "error_message": "An unexpected error occurred. Please try again later."
        })
# client signin process handling

def client_signin(request):
    """
    Handles client sign-in.
    """
    message = ''
    
    if request.method == "POST":
        try:
            # Extract user input
            username = request.POST.get("username", "").strip()
            password = request.POST.get("password", "").strip()

            # Validate username number (Assuming 10-digit format for India)
            if not username or not password:
                return render(request, "client_signin.html", {
                    "message": "username number and password are required."
                })
            
            if not username.isdigit() or len(username) != 10:
                return render(request, "client_signin.html", {
                    "message": "Invalid username number. It should be a 10-digit number."
                })
            
            print("username", username)
            print("password", password)
            
            user = authenticate(username=username, password=password)
            print("user", user)

            if user is not None:
                print("client user")
                if is_client(user):
                    print("staff user authenticated")
                    login(request, user)
                    print("staff user logged in",request.user.username)
                    logger.info("User %s logged in successfully.", user.username)
                    return redirect("/dashboard")
                else:
                    logger.warning("Failed login attempt for username: %s", username)
                    return render(request, "client_signin.html", {
                        "message": "Not authorized to access this page."
                    })

            else:
                print("client user not authenticated")
                logger.warning("Failed login attempt for username: %s", username)
                return render(request, "client_signin.html", {
                    "message": "Invalid username number or password. Please try again or create an account."
                })

        
        except Exception as e:
            logger.exception("Error during client login: %s", str(e))
            return render(request, "client_error.html", {
                "message": "An unexpected error occurred. Please try again later."
            })

    return render(request, "client_signin.html")

def client_forget_id(request):
    """
    Handles client signup via phone number and OTP verification.
    """
    try:
        message = ""

        if request.method == "POST":
            user_id = request.POST.get("mobile")

            if not user_id:
                return JsonResponse({"error": "Mobile number is required"}, status=400)

            # Check if user already exists
            if not User.objects.filter(username=user_id, groups__name='CLIENT').exists():
                message = "Mobile number not registered!"
                return render(request, "client_forget_id.html", {"message": message})

            # Generate OTP token
            data = token()
            request.session["user_id"] = user_id
            request.session["token"] = data["token"]

            # Send OTP
            response = send_phone_otp(user_id, data["token"])
            response_data = response.get("data", {})

            if response.get("responseCode") in [200, 506]:
                request.session["verificationId"] = response_data.get("verificationId")
                logger.info(f"OTP sent successfully to {user_id}")
                return redirect("/clientotp")

            message = "Retry sending OTP"
            logger.warning(f"Failed OTP attempt for {user_id}: {response}")

        return render(request, "client_forget_id.html", {"message": message})

    except Exception as e:
        logger.exception("Error occurred during client signup")
        return render(request, "client_error.html", {"error_message": "An unexpected error occurred. Please try again later."})

def client_otp_forget(request):
    """
    Handles OTP verification for user authentication.
    """
    try:
        message = ""

        if request.method == "POST":
            otp = request.POST.get("otp")

            # Validate OTP input
            if not otp:
                return JsonResponse({"error": "OTP is required"}, status=400)

            # Retrieve session data
            user_id = request.session.get("user_id")
            token = request.session.get("token")
            verification_id = request.session.get("verificationId")

            if not user_id or not token or not verification_id:
                logger.error("Session data missing for OTP verification")
                return render(request, "client_error.html", {"error_message": "Session expired. Please restart the process."})

            logger.info(f"Verifying OTP for user: {user_id}")

            # Verify OTP
            response = verify_otp(user_id, otp, verification_id, token)

            if response.get("responseCode") == 200:
                response_data = response.get("data", {})
                request.session["verificationStatus"] = response_data.get("verificationStatus")

                logger.info(f"OTP verified successfully for {user_id}")
                return redirect("/clientpassword")

            message = "Wrong OTP. Please enter the correct OTP."
            logger.warning(f"Incorrect OTP entered for {user_id}")

        return render(request, "client_otp.html", {"message": message})

    except Exception as e:
        logger.exception("Error occurred during OTP verification")
        return render(request, "client_error.html", {"error_message": "An unexpected error occurred. Please try again later."})

def client_signup_password_forget(request):
    """
    Handles client password setup after OTP verification.
    """
    try:
        if request.method == "POST":
            user_id = request.session.get("user_id")
            verification_status = request.session.get("verificationStatus")
            password = request.POST.get("password")

            # Validate session data
            if not user_id or verification_status != "VERIFICATION_COMPLETED":
                logger.warning("Session expired or invalid verification status for user: %s", user_id)
                return redirect("/forget-password")

            # Validate password
            if not password or len(password) < 6:
                logger.warning("Weak password attempt for user: %s", user_id)
                return render(request, "client_password.html", {"error": "Password must be at least 6 characters long."})

            # Check if user not already exists
            if not User.objects.filter(username=user_id).exists():
                logger.warning("User doesn't exists: %s", user_id)
                return render(request, "client_password.html", {"error": "User not exists. Please signup instead."})

           # Check if user exists
            user, created = User.objects.get_or_create(username=user_id)

            # Update password (whether new or existing user)
            user.set_password(password)
            user.save()

            authenticated_user = authenticate(username=user_id, password=password)
            if authenticated_user is not None:
                login(request, authenticated_user)
                logger.info("User signed up and logged in: %s", user_id)
                return redirect("/dashboard")

            logger.error("User authentication failed after signup: %s", user_id)
            return render(request, "client_password.html", {"error": "Account creation failed. Please try again."})

        return render(request, "client_password.html")

    except Exception as e:
        logger.exception("Unexpected error in client_signup_password")
        return render(request, "client_error.html", {"error_message": "An error occurred. Please try again later."})

@login_required(login_url='/signin')
def dashboard(request):
    """
    Handles the client service page rendering.
    """
    try:
        user = request.user
        logger.info(f"Accessing client service page for user: {user.username} (ID: {user.id})")

        # Fetch client info
        client = ClientProfile.objects.filter(user=user).first()
        if not client:
            logger.warning(f"No ClientInfo found for user: {user.username}")
            return JsonResponse({"error": "Client information not found."}, status=404)

        # Fetch frame user information
        service_data = ServiceAvail.objects.filter(client_id=client)
        context = {
            "client": client,
            "service": service_data,
        }

        return render(request, "choose_service.html", context)

    except Exception as e:
        logger.exception("Error occurred while loading client service page")
        return JsonResponse({"error": "An internal server error occurred."}, status=500)

@login_required(login_url='/signin')
def service_statitiscs(request, id):
    """
    Renders the client dashboard with their profile information and services.
    """
    try:
        user = request.user
        print(user)
        logger.info(f"Accessing dashboard for user: {user.username} (ID: {user.id})")

        # Fetch client info
        client = ClientProfile.objects.filter(user=user).first()
        if not client:
            logger.warning(f"No ClientInfo found for user: {user.username}")
            return JsonResponse({"error": "Client information not found."}, status=404)

        # Fetch frame user information
        service_data = ServiceAvail.objects.filter(client_id=client, id=id).first()

        serv_stats = ServiceStatistics.objects.filter(service_id=service_data).all()
        print(ServiceStatistics.objects.filter(service_id=service_data).exists())

        daily_click_stats = (ServiceStatistics.objects
        .filter(service_id=service_data)
        .annotate(day=TruncDate('timestamp'))
        .values('day')
        .annotate(
        unique_clicks=Count('ip_address', distinct=True),
        total_clicks=Sum('impressions')
        )
        .order_by('day'))
        
        click_stats_map = OrderedDict()

        for item in daily_click_stats:
            date_str = item['day'].strftime('%Y-%m-%d')  # or any format you prefer
            click_stats_map[date_str] = [
                item['unique_clicks'],
                item['total_clicks']
                ]
            
        context = {
            "client": client,
            "service": service_data,
            "serv_stats": serv_stats,
            "click_stats_map": click_stats_map,

            
        }

        return render(request, "client_dashboard.html", context)

    except Exception as e:
        logger.exception("Error occurred while loading client dashboard")
        return JsonResponse({"error": "An internal server error occurred."}, status=500)

@login_required(login_url='/signin')
def client_logout(request):
    """
    Handles user logout and redirects to the login page.
    """
    try:
        logout(request)
        logger.info("User logged out successfully.")
        return redirect("/signin")
    except Exception as e:
        logger.exception("Error during logout: %s", str(e))
        return render(request, "client_error.html", {
            "error_message": "An unexpected error occurred. Please try again later."
        })
    
def create_client(request):
    """
    Handles the creation of a new client profile.
    """

    try:
        if request.method == "POST":
            # Extract form data
            name = request.POST.get("name", "").strip()
            business_name = request.POST.get("businessname", "").strip()
            website_url = request.POST.get("businesswebsite", "").strip()
            business_description = request.POST.get("businessdescription", "").strip()
            business_size = request.POST.get("businesssize", "").strip()
            business_industry = request.POST.get("businessindustry", "").strip()
            email = request.POST.get("emailid", "").strip()
            address = request.POST.get("address", "").strip()
            pin_code = request.POST.get("pincode", "").strip()
            city = request.POST.get("city", "").strip()
            contact = request.POST.get("contact", "").strip()
            state = request.POST.get("state", "").strip()
            country = request.POST.get("country", "").strip()

            # Input Validation
            if not name or not business_name or not email or not contact:
                return render(request, "client_form.html", {
                    "error": "Name, Business Name, Email, and Contact are required fields."
                })

            # Validate email format
            try:
                validate_email(email)
                
            except ValidationError:
                return render(request, "client_form.html", {
                    "error": "Invalid email format. Please enter a valid email address."
                })

            # Validate pin code (assuming Indian 6-digit format)
            if pin_code and (not pin_code.isdigit() or len(pin_code) != 6):
                return render(request, "client_form.html", {
                    "error": "Invalid Pin Code. It should be a 6-digit number."
                })

            # Validate contact number (assuming 10-digit Indian format)
            if contact and (not contact.isdigit() or len(contact) != 10):
                return render(request, "client_form.html", {
                    "error": "Invalid Contact Number. It should be a 10-digit number."
                })


            # Save to the database
            client_info=ClientProfile()

            if User.objects.filter(username=contact).exists():
                # User with this username already exists
                return render(request, "client_form.html", {
                    "error": "Client email already exists. You cannot create multiple profiles."
                })
            else:
                # User does not exist, so create them
                user = User.objects.create_user(
                    username=contact,
                    email=email,
                    password="12345678",  #  Get this from a form in real app
                )
                user.save()

                # Add user to a group
                group_name = "CLIENT"  # Replace with your actual group name
                group, created = Group.objects.get_or_create(name=group_name)
                user.groups.add(group)

            
            client_info.user=user
            client_info.name=name
            client_info.business_name=business_name
            client_info.website_url=website_url
            client_info.business_description=business_description
            client_info.business_size=business_size
            client_info.business_industry=business_industry
            client_info.email=email
            client_info.address=address
            client_info.pin_code=pin_code
            client_info.city=city
            client_info.contact=contact
            client_info.state=state
            client_info.country=country

            print("client info", client_info)
            print("client info", client_info.user.username)

            client_info.save()


            # Send a welcome email to the client
            # if User.objects.filter(username=email).exists():
            #     try:
            #         send_email(
            #             subject="Welcome to Our Service",
            #             message=f"Hello {name},\n\nThank you for signing up! Your client profile has been created successfully.\n\nBest regards,\nYour Company",
            #             recipient_list=[email]
            #         )
            #     except Exception as e:
            #         logger.error("Failed to send email: %s", str(e))
            #         return render(request, "client_form.html", {
            #             "error": "Failed to send welcome email. Please check your email settings."
            #         })
    
            logger.info("Client information saved successfully for user: %s", user.username)
            return redirect("/staff-dashboard")

    except Exception as e:
        logger.exception("Error while saving client information for user: %s", user.username)
        return render(request, "client_form.html", {
            "error": "An unexpected error occurred. Please try again later."
        })

    return render(request, "client_form.html")

def client_details(request, id):
    """
    Displays the details of a specific client.
    """
    try:
        # Fetch the ClientProfile instance
        client = get_object_or_404(ClientProfile, id=id)

        # # Fetch the associated frame users
        client_services = ServiceAvail.objects.filter(client_id=client)

        logger.info(f"Accessing client details for Client ID: {id}")

        return render(
            request,
            "client_details.html",
            context={
                "client": client,
                "client_services": client_services
            }
        )

    except Exception as e:
        logger.exception("Error occurred while loading client details")
        return JsonResponse({"error": "An internal server error occurred."}, status=500)

def create_service(request, id):
    """
    Handles the creation of a new service for a specific client.
    """
    try:
        # Fetch the ClientProfile instance
        client = get_object_or_404(ClientProfile, id=id)

        if request.method == "POST":
            # Extract form data
            service_type = request.POST.get("service_type", "").strip()
            campaingn_description = request.POST.get("description", "").strip()
            enabled = request.POST.get("status", "").strip()
            target_img = request.FILES.get('tarimageUpload')
            reference_img = request.FILES.get('refimageUpload')
            overlap_video = request.FILES.get('videoUpload')
            height = request.POST.get("height", "").strip()
            width = request.POST.get("width", "").strip()
            redirect_url = request.POST.get("redirect_url", "").strip()
            campaign_name = request.POST.get("campaign_name", "").strip()
            campaign_days = request.POST.get("campaign_days", "").strip()


            # Input Validation
            if not service_type or not campaingn_description or not enabled:
                return render(request, "create_services.html", {
                    "error": "Service Type, Description, and Price are required fields."
                })

            # Save to the database
            service = ServiceAvail()
            service.client_id = client
            service.service_type = ServiceType.objects.get(service_type=service_type)
            service.campaingn_description = campaingn_description
            service.enabled = True if enabled.lower() == "true" else False
            service.height = height
            service.width = width
            service.redirect_url = redirect_url
            service.campaign_name = campaign_name
            service.campaign_days = campaign_days


            if overlap_video:
                # # Generate a new filename
                # file_extension = os.path.splitext(overlap_video.name)[1]  # Get the file extension
                # new_file_name = f"{client.business_name}{timezone.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
                # # new_file_name = f"{uuid.uuid4().hex}{file_extension}" #another way to generate unique name

                # # Save the file with the new name
                # file_path = default_storage.save(new_file_name, ContentFile(overlap_video.read()))
                # service.overlap_video = file_path  # Save the path to the file
                service.overlap_video = overlap_video

            if target_img:
                # # Generate a new filename
                # file_extension = os.path.splitext(target_img.name)[1]
                # new_file_name = f"{client.business_name}{timezone.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
                # # new_file_name = f"{uuid.uuid4().hex}{file_extension}" #another way to generate unique name
                # # Save the file with the new name   
                # # Save the file with the new name
                # file_path = default_storage.save(new_file_name, ContentFile(target_img.read()))
                # service.target_img = file_path  # Save the path to the file
                service.target_img = target_img  # Save the path to the file

            if reference_img:
                # # Generate a new filename
                # file_extension = os.path.splitext(reference_img.name)[1]
                # new_file_name = f"{client.business_name}{timezone.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
                # # new_file_name = f"{uuid.uuid4().hex}{file_extension}" #another way to generate unique name
                # # Save the file with the new name   
                # # Save the file with the new name
                # file_path = default_storage.save(new_file_name, ContentFile(reference_img.read()))
                # service.reference_img = file_path  # Save the path to the file
                service.reference_img = reference_img  # Save the path to the file


            service.save()

            logger.info("Service created successfully for client: %s", client.name)
            return redirect(f"/client-details/{id}")
        
        return render(request, "create_services.html")

    except Exception as e:
        logger.exception("Error while creating service for client: %s", client.name)
        return render(request, "create_services.html", {
            "error": "An unexpected error occurred. Please try again later."
        })  

def assets(request, id):
    """
    Handles the upload of assets for a specific client.
    """
    try:
        # Fetch the FrameUserInfo instance
        service = get_object_or_404(ServiceAvail, id=id)
        print("service")
        print(service)
        client_id = service.client_id
        print(client_id)
        if request.method == "POST":
            # Extract form data
            file_name = request.FILES.get('file_name')
            upload_type = request.POST.get("type", "").strip()

            print("overlap:",file_name)
            print("uploadtype:",upload_type)

            # Input Validation
            if not file_name and not upload_type:
                print("file name not found")
                return render(request, "assets.html", {
                    "serv": service,
                    "error": "All fields are required."
                })
            
            if not upload_type or upload_type not in ["overlap_video", "target_img", "reference_img"]:
                print("upload type not found")
                return render(request, "assets.html", {
                    "serv": service,
                    "error": "Invalid upload type."
                })
            if upload_type == "overlap_video" and service.overlap_video:
                os.remove(service.overlap_video.path)
                service.overlap_video=file_name
            elif upload_type == "target_img" and service.target_img:
                os.remove(service.target_img.path)
                service.target_img=file_name
            elif upload_type == "reference_img" and service.reference_img:
                os.remove(service.reference_img.path)
                service.reference_img=file_name
            else:
                return render(request, "assets.html", {
                    "serv": service,
                    "error": "Invalid upload type."
                })
            # Save the file with the new name

            service.save()

            logger.info("Assets uploaded successfully for Frame User ID: %s", client_id)
            return redirect("/staff-dashboard")
        
        
        return render(request, "assets.html",context={
                "serv": service,
            })

    except Exception as e:
        logger.exception("Error while uploading assets")
        return render(request, "client_error.html", {
            "error_message": "An unexpected error occurred. Please try again later."
        })

def generate_qr(request, frameuserid):
    """
    Generates a QR code for a given frame user ID.
    Returns a PNG image containing the QR code.
    """
    try:
        # Validate frameuserid
        if not frameuserid:
            logger.error("Invalid frameuserid provided.")
            return JsonResponse({"error": "Invalid user ID"}, status=400)

        # Encode the user ID
        userid_hash = encode_primary_key(frameuserid)

        # Construct the media URL
        media_url = request.build_absolute_uri(f'/userex/{userid_hash}')
        logger.info(f"Generating QR Code for: {media_url}")

        # Create the QR code
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(media_url)
        qr.make(fit=True)

        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")

        # Prepare response
        response = HttpResponse(content_type="image/png")
        img.save(response, "PNG")

        return response

    except Exception as e:
        logger.exception("Error generating QR code")
        return JsonResponse({"error": "Internal server error"}, status=500)

def user_ex(request, hasheduserid):
    """
    Retrieves and displays the associated web video for a given user.
    """
   
    try:
        userid = decode_primary_key(hasheduserid)
        service = get_object_or_404(ServiceAvail, id=userid)
        print(service)

        if service.enabled:

            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
            print("ip address", ip)

            ser_ip = ServiceStatistics.objects.filter(service_id=service, ip_address=ip).first()
            if ser_ip:
                print("ip already exists")
                ser_ip.impressions = F('impressions') + 1
                ser_ip.save()
            else:
                print("ip not exists")
                ser_ip = ServiceStatistics.objects.create(
                    service_id=service,
                    ip_address=ip,
                    timestamp=now(),
                    clicks=0,
                    impressions=1,
                )
                ser_ip.save()
            
            if service.overlap_video and service.service_type.service_type == "BASIC":
                return render(request, "basic_page.html", {"media": service})
            
            elif service.overlap_video and service.service_type.service_type == "PREMIUM":
                return render(request, "premium_page.html", {"media": service})
            
            elif service.overlap_video and service.service_type.service_type == "PREMIUM_PLUS":
                return render(request, "premium_plus_page.html", {"media": service})
            
        else:
            return render(request, "disabled.html")

        logger.warning(f"No video found for user {userid}")
        return JsonResponse({"error": "No video found"}, status=404)

    except Exception as e:
        logger.exception("Error in camera_feed: %s", str(e))
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)

def logout_view(request):
    """
    Handles user logout.
    """
    try:
        logout(request)
        logger.info("User logged out successfully.")
        return redirect("/staff-signin")
    except Exception as e:
        logger.exception("Error during logout: %s", str(e))
        return render(request, "client_error.html", {
            "error_message": "An unexpected error occurred. Please try again later."
        })

# Aliveframe AR Games

def ar_burger_game_landing(request,hashid):
    print("hasheduserid",hashid)
    """
    Renders the AR games page.
    """
    try:
        userid = decode_primary_key(hashid)
        print("userid", userid)
        burgergame = BurgerGame.objects.filter(id=userid).first()
        print("burgergame", burgergame)
        burgerscore = BurgerScore.objects.filter(game=burgergame).first()
        print("burgerscore", burgerscore)
        player_name="----"
        score=0

        if burgerscore:
            player_name=burgerscore.player_name
            score=burgerscore.score

        return render(request, "burger_game_landing.html",context={
                "burgergame": burgergame,
                "player_name": player_name,
                "score": score,
                "hashid": hashid,
            })
    except Exception as e:
        logger.exception("Error while loading AR games page")
        return render(request, "client_error.html", {
            "error_message": "An unexpected error occurred. Please try again later."
        })

def burger_game(request, name, hashid):
    """
    Renders the AR games page.
    """
    try:
        userid = decode_primary_key(hashid)
        print("userid", userid)
        burgergame = BurgerGame.objects.filter(id=userid).first()
        print("burgergame", burgergame)

        return render(request, "burger_game.html",context={
                "burgergame": burgergame,
                "player_name": name,
            })
    except Exception as e:
        logger.exception("Error while loading AR games page")
        return render(request, "client_error.html", {
            "error_message": "An unexpected error occurred. Please try again later."
        })

def update_burger_score(request):
    """
    Updates the burger game score.
    """
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            score = data.get("score")
            name = data.get("name")
            print("score", score)
            print("name", name)

            logger.info("Burger game score updated successfully for player: %s", name)
            return JsonResponse({"message": "Score updated successfully"}, status=200)

    except Exception as e:
        logger.exception("Error while updating burger game score")
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)


def ar_game_landing(request,hashid):
    """
    Renders the AR games page.
    """
    try:
        userid = decode_primary_key(hashid)
        print("userid", userid)
        if request.method == "POST":
            name = request.POST.get("name", "").strip()
            mobile = request.POST.get("mobile", "").strip()
            print("name", name)
            print("mobile", mobile)

            request.session["name"] = name
            request.session["mobile"] = mobile

            return redirect(f"/play-ar-game/{hashid}")

        argame = ArGame.objects.filter(id=userid).first()
        return render(request, "game/landing.html", context={
            "logo": argame.logo.url if argame.logo else None,
            "company_name": argame.company_name,
            "video_file": argame.video_file.url if argame.video_file else None,
            "website_url": argame.website_url,
            "hashid": hashid,
        })
    except Exception as e:
        logger.exception("Error while loading AR games page")
        return render(request, "client_error.html", {
            "error_message": "An unexpected error occurred. Please try again later."
        })
    
def play_ar_game(request, hashid):
    """
    Renders the AR games page.
    """
    try:
        userid = decode_primary_key(hashid)
        print("userid", userid)
        argame = ArGame.objects.filter(id=userid).first()
        return render(request, "game/game_page.html", context={
            "max_size": argame.max_size,
            "min_size": argame.min_size,
            "min_distance": argame.min_distance,
            "max_distance": argame.max_distance,
            "glb_file": argame.glb_file.url if argame.glb_file else None,
            "fixed_value": argame.fixed_value,
            "hashid": hashid,
        })
    except Exception as e:
        logger.exception("Error while loading AR games page")
        return render(request, "client_error.html", {
            "error_message": "An unexpected error occurred. Please try again later."
        })

@csrf_exempt
def update_ar_game_score(request):
    """
    Updates the AR game score.
    """
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            score = data.get("score")
            print("score", score)
            name = request.session.get("name", "Anonymous")
            mobile = request.session.get("mobile", "Unknown")
            score = int(score)
            request.session["score"] = score

            hashid = data.get("hashid")
            userid = decode_primary_key(hashid)

            # Save the score to the database

            existing_score = ArGameScore.objects.filter(game_id=userid, contact=mobile).first()
            if existing_score :
                existing_score.score = score  # Update only if the new score is higher
                existing_score.player_name = name  # Update player name as well
                existing_score.save()
                return JsonResponse({"message": "Score updated successfully"}, status=200)
            
            else:
                ArGameScore.objects.create(
                    player_name=name,
                    contact=mobile,
                    score=score,
                    game_id=userid
                )

            logger.info("AR game score updated successfully for player: %s", name)
            return JsonResponse({"message": "Score updated successfully"}, status=200)

    except Exception as e:
        logger.exception("Error while updating AR game score")
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)
    
def ar_game_leaderboard(request, hashid):
    """
    Renders the AR game leaderboard page.
    """
    try:
        userid = decode_primary_key(hashid)
        print("userid", userid)
        current_player_score = None
        current_player_name = None
        if request.session.get("score") is not None:
            current_player_score = request.session.get("score")
            current_player_name = request.session.get("name", "Anonymous")
        argame = ArGame.objects.filter(id=userid).first()
        top_players = ArGameScore.objects.filter(game=argame).order_by('-score')[:10]
        return render(request, "game/leaderboard.html", context={
            "top_players": top_players,
            "argame": argame,
            "current_player_score": current_player_score,
            "current_player_name": current_player_name,
            "hashid": hashid,
        })
    except Exception as e:
        logger.exception("Error while loading AR game leaderboard page")
        return render(request, "client_error.html", {
            "error_message": "An unexpected error occurred. Please try again later."
        })
    

    
def contact(request):
    """
    Handles the contact form submission.
    """
    try:
        if request.method == "POST":
            name = request.POST.get("name", "").strip()
            business_name = request.POST.get("businessname", "").strip()
            contact = request.POST.get("contact", "").strip()
            email = request.POST.get("email", "").strip()
            message = request.POST.get("message", "").strip()

            # Input Validation
            if not name or not business_name or not email or not contact:
                return render(request, "contact.html", {
                    "error": "Name, Business Name, Email, and Contact are required fields."
                })

            # Validate email format
            try:
                validate_email(email)
                
            except ValidationError:
                return render(request, "contact.html", {
                    "error": "Invalid email format. Please enter a valid email address."
                })

            # Validate contact number (assuming 10-digit Indian format)
            if contact and (not contact.isdigit() or len(contact) != 10):
                return render(request, "contact.html", {
                    "error": "Invalid Contact Number. It should be a 10-digit number."
                })

            # Save to the database
            contact_info = ContactUs(
                name=name,
                business_name=business_name,
                contact=contact,
                email=email,
                message=message
            )
            contact_info.save()

            logger.info("Contact information saved successfully for user: %s", name)
            return redirect("/")

    except Exception as e:
        logger.exception("Error while saving contact information")
        return render(request, "client_error.html", {
            "error_message": "An unexpected error occurred. Please try again later."
        })

    return render(request, "contact.html")

def aboutus(request):
    """
    Renders the About Us page.
    """
    try:
        return render(request, "about_us.html")
    except Exception as e:
        logger.exception("Error while loading About Us page")
        return render(request, "client_error.html", {
            "error_message": "An unexpected error occurred. Please try again later."
        })

def privacypolicy(request):
    """
    Renders the Privacy Policy page.
    """
    try:
        return render(request, "privacy_policy.html")
    except Exception as e:
        logger.exception("Error while loading Privacy Policy page")
        return render(request, "client_error.html", {
            "error_message": "An unexpected error occurred. Please try again later."
        })
    
def term_and_condition(request):
    """
    Renders the Terms and Conditions page.
    """
    try:
        return render(request, "terms_and_condition.html")
    except Exception as e:
        logger.exception("Error while loading Terms and Conditions page")
        return render(request, "client_error.html", {
            "error_message": "An unexpected error occurred. Please try again later."
        })

def blog_page(request):
    """
    Renders the Blog page.
    """
    try:
        return render(request, "blog.html")
    except Exception as e:
        logger.exception("Error while loading Blog page")
        return render(request, "client_error.html", {
            "error_message": "An unexpected error occurred. Please try again later."
        })