from django.contrib.auth import login, authenticate, logout
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render,redirect
from django.conf import settings
from photo_frame.models import *
from photo_frame import forms
from .utils import *
import qrcode
import os
from django.http import HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import razorpay
from django.contrib.auth import logout
from django.shortcuts import redirect
import logging
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib import messages

# authorize razorpay client with API Keys.
razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))


# from .models import MediaData

# For web experience

# Configure logging
logger = logging.getLogger(__name__)

@login_required(login_url='/frame/signin')
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
        media_url = request.build_absolute_uri(f'/frame/qr/userex/{userid_hash}')
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


@login_required(login_url='/frame/signin')
def user_dashboard(request):
    """
    Renders the user dashboard with client information, frame user details, 
    and frame usage statistics.
    """
    try:
        user = request.user
        logger.info(f"Accessing dashboard for user: {user.username} (ID: {user.id})")

        # Fetch client info
        client = ClientInfo.objects.filter(user=user).first()
        if not client:
            logger.warning(f"No ClientInfo found for user: {user.username}")
            return JsonResponse({"error": "Client information not found."}, status=404)

        # Fetch frame user information
        frame_users = FrameUserInfo.objects.filter(client_id=client)
        
        # Fetch frame count details
        frame_count = FrameCount.objects.filter(client_id=client).first()

        # Calculate frame statistics
        left_frames = frame_count.frame_count if frame_count else 0
        used_frames = frame_users.count()
        total_frames = left_frames + used_frames

        context = {
            "client": client,
            "frame_users": frame_users,
            "frame_count": frame_count,
            "left_frames": left_frames,
            "used_frames": used_frames,
            "total_frames": total_frames
        }

        return render(request, "photo_frame/user_dashboard.html", context)

    except Exception as e:
        logger.exception("Error occurred while loading user dashboard")
        return JsonResponse({"error": "An internal server error occurred."}, status=500)

@login_required(login_url='/frame/signin')
def user_dashboard_search(request, id):
    """
    Searches and displays the user dashboard with client and frame details based on a given ID.
    """
    try:
        user = request.user
        logger.info(f"User {user.username} (ID: {user.id}) is accessing dashboard search with ID: {id}")

        # Fetch client info
        client = get_object_or_404(ClientInfo, user=user)

        # Fetch frame user information
        frame_users = FrameUserInfo.objects.filter(client_id=client)

        # Fetch frame count details
        frame_count = FrameCount.objects.filter(client_id=client).first()

        if not frame_count:
            logger.warning(f"No FrameCount found for client: {client.id}")
            left_frames = used_frames = total_frames = 0
        else:
            left_frames = frame_count.frame_count
            used_frames = frame_users.count()
            total_frames = left_frames + used_frames

        context = {
            "client": client,
            "frame_users": frame_users,
            "frame_count": frame_count,
            "left_frames": left_frames,
            "used_frames": used_frames,
            "total_frames": total_frames
        }

        return render(request, "user_dashboard.html", context)

    except Exception as e:
        logger.exception("Error occurred while loading user dashboard search")
        return JsonResponse({"error": "An internal server error occurred."}, status=500)

@login_required(login_url='/frame/signin')
def customer_data(request, id):
    """
    Handles customer data retrieval and media upload for a specific frame user.
    """
    try:
        # Fetch the FrameUserInfo instance
        frame_user = get_object_or_404(FrameUserInfo, id=id)

        # Fetch the associated media
        frame_media = MediaForWebExperience.objects.filter(user=frame_user).first()

        logger.info(f"Accessing customer data for FrameUser ID: {id}")
        print(frame_media.web_video.url)
        print(frame_media.reference_img.url)

        if request.method == "POST":
            
            uploaded_video = request.FILES.get('videoUpload')
            
            if uploaded_video:
                if not frame_media:
                    logger.warning(f"No MediaForWebExperience found for FrameUser ID: {id}")
                    return JsonResponse({"error": "Media not found for this frame user."}, status=404)
                os.remove(frame_media.web_video.path)
                frame_media.web_video = uploaded_video
                frame_media.save()
                logger.info(f"Video uploaded successfully for FrameUser ID: {id}")

        return render(
            request,
            "photo_frame/customer_details.html",
            context={
                "frame_user": frame_user,
                "frame_media": frame_media
            }
        )

    except Exception as e:
        logger.exception("Error occurred while handling customer data")
        return JsonResponse({"error": "An internal server error occurred."}, status=500)

def client_signup(request):
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
            if User.objects.filter(username=user_id).exists():
                message = "Mobile number already exists!"
                return render(request, "photo_frame/client_signup.html", {"message": message})

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
                return redirect("/frame/enterotp")

            message = "Retry sending OTP"
            logger.warning(f"Failed OTP attempt for {user_id}: {response}")

        return render(request, "photo_frame/client_signup.html", {"message": message})

    except Exception as e:
        logger.exception("Error occurred during client signup")
        return render(request, "photo_frame/client_error.html", {"error_message": "An unexpected error occurred. Please try again later."})

def otp(request):
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
                return render(request, "photo_frame/client_error.html", {"error_message": "Session expired. Please restart the process."})

            logger.info(f"Verifying OTP for user: {user_id}")

            # Verify OTP
            response = verify_otp(user_id, otp, verification_id, token)

            if response.get("responseCode") == 200:
                response_data = response.get("data", {})
                request.session["verificationStatus"] = response_data.get("verificationStatus")

                logger.info(f"OTP verified successfully for {user_id}")
                return redirect("/frame/client-password")

            message = "Wrong OTP. Please enter the correct OTP."
            logger.warning(f"Incorrect OTP entered for {user_id}")

        return render(request, "photo_frame/client_otp.html", {"message": message})

    except Exception as e:
        logger.exception("Error occurred during OTP verification")
        return render(request, "photo_frame/client_error.html", {"error_message": "An unexpected error occurred. Please try again later."})
    

def client_signup_password(request):
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
                return redirect("/frame/client-signup")

            # Validate password
            if not password or len(password) < 6:
                logger.warning("Weak password attempt for user: %s", user_id)
                return render(request, "photo_frame/photo_frame/client_password.html", {"error": "Password must be at least 6 characters long."})

            # Check if user already exists
            if User.objects.filter(username=user_id).exists():
                logger.warning("User already exists: %s", user_id)
                return render(request, "photo_frame/client_password.html", {"error": "User already exists. Please log in instead."})

            # Create and authenticate user
            user = User.objects.create_user(username=user_id, password=password)
            user.save()

            authenticated_user = authenticate(username=user_id, password=password)
            if authenticated_user is not None:
                login(request, authenticated_user)
                logger.info("User signed up and logged in: %s", user_id)
                return redirect("/frame/client-form")

            logger.error("User authentication failed after signup: %s", user_id)
            return render(request, "photo_frame/client_password.html", {"error": "Account creation failed. Please try again."})

        return render(request, "photo_frame/client_password.html")

    except Exception as e:
        logger.exception("Unexpected error in client_signup_password")
        return render(request, "photo_frame/client_error.html", {"error_message": "An error occurred. Please try again later."})

def client_forget_pswd(request):
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
                return render(request, "photo_frame/client_signup.html", {"message": message})

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
                return redirect("/frame/otp")

            message = "Retry sending OTP"
            logger.warning(f"Failed OTP attempt for {user_id}: {response}")

        return render(request, "photo_frame/client_signup_forget.html", {"message": message})

    except Exception as e:
        logger.exception("Error occurred during client signup")
        return render(request, "photo_frame/client_error.html", {"error_message": "An unexpected error occurred. Please try again later."})

def otp_forget(request):
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
                return render(request, "photo_frame/client_error.html", {"error_message": "Session expired. Please restart the process."})

            logger.info(f"Verifying OTP for user: {user_id}")

            # Verify OTP
            response = verify_otp(user_id, otp, verification_id, token)

            if response.get("responseCode") == 200:
                response_data = response.get("data", {})
                request.session["verificationStatus"] = response_data.get("verificationStatus")

                logger.info(f"OTP verified successfully for {user_id}")
                return redirect("/frame/password")

            message = "Wrong OTP. Please enter the correct OTP."
            logger.warning(f"Incorrect OTP entered for {user_id}")

        return render(request, "photo_frame/client_forget_otp.html", {"message": message})

    except Exception as e:
        logger.exception("Error occurred during OTP verification")
        return render(request, "photo_frame/client_error.html", {"error_message": "An unexpected error occurred. Please try again later."})


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
                return redirect("/frame/forget-password")

            # Validate password
            if not password or len(password) < 6:
                logger.warning("Weak password attempt for user: %s", user_id)
                return render(request, "photo_frame/client_password.html", {"error": "Password must be at least 6 characters long."})

            # Check if user not already exists
            if not User.objects.filter(username=user_id).exists():
                logger.warning("User doesn't exists: %s", user_id)
                return render(request, "photo_frame/client_forget_password.html", {"error": "User not exists. Please signup instead."})

           # Check if user exists
            user, created = User.objects.get_or_create(username=user_id)

            # Update password (whether new or existing user)
            user.set_password(password)
            user.save()

            authenticated_user = authenticate(username=user_id, password=password)
            if authenticated_user is not None:
                login(request, authenticated_user)
                logger.info("User signed up and logged in: %s", user_id)
                return redirect("/frame/dashboard")

            logger.error("User authentication failed after signup: %s", user_id)
            return render(request, "photo_frame/client_forget_password.html", {"error": "Account creation failed. Please try again."})

        return render(request, "photo_frame/client_forget_password.html")

    except Exception as e:
        logger.exception("Unexpected error in client_signup_password")
        return render(request, "photo_frame/client_error.html", {"error_message": "An error occurred. Please try again later."})

@login_required(login_url='/frame/signin')
def client_form(request):
    """
    Handles client information submission.
    """
    user = request.user
    if request.method == "POST":
        try:
            # Extract form data
            name = request.POST.get("name", "").strip()
            business_name = request.POST.get("businessname", "").strip()
            email = request.POST.get("emailid", "").strip()
            address = request.POST.get("address", "").strip()
            pin_code = request.POST.get("pincode", "").strip()
            city = request.POST.get("city", "").strip()
            contact = request.POST.get("contact", "").strip()
            state = request.POST.get("state", "").strip()
            country = request.POST.get("country", "").strip()
           

            # Input Validation
            if not name or not business_name or not email or not contact:
              
                return render(request, "photo_frame/client_details.html", {
                    "error": "Name, Business Name, Email, and Contact are required fields."
                })

            # Validate email format
            try:
                validate_email(email)
                
            except ValidationError:
                return render(request, "photo_frame/client_details.html", {
                    "error": "Invalid email format. Please enter a valid email address."
                })

            # Validate pin code (assuming Indian 6-digit format)
            if pin_code and (not pin_code.isdigit() or len(pin_code) != 6):
               
                return render(request, "photo_frame/client_details.html", {
                    "error": "Invalid Pin Code. It should be a 6-digit number."
                })

            # Validate contact number (assuming 10-digit Indian format)
            if contact and (not contact.isdigit() or len(contact) != 10):
              
                return render(request, "photo_frame/client_details.html", {
                    "error": "Invalid Contact Number. It should be a 10-digit number."
                })

            # Check if the user already has a client profile
            if ClientInfo.objects.filter(user=user).exists():
              
                return render(request, "photo_frame/client_details.html", {
                    "error": "Client profile already exists. You cannot create multiple profiles."
                })

            # Save to the database
            client_info=ClientInfo()
            
            client_info.user=user
            client_info.name=name
            client_info.business_name=business_name
            client_info.email=email
            client_info.address=address
            client_info.pin_code=pin_code
            client_info.city=city
            client_info.contact=contact
            client_info.state=state
            client_info.country=country
            
            client_info.save()

          
            
            logger.info("Client information saved successfully for user: %s", user.username)
            return redirect("/frame/dashboard")

        except Exception as e:
            logger.exception("Error while saving client information for user: %s", user.username)
            return render(request, "photo_frame/client_details.html", {
                "error": "An unexpected error occurred. Please try again later."
            })

    return render(request, "photo_frame/client_details.html")

def client_signin(request):
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
                return render(request, "photo_frame/client_signin.html", {
                    "message": "Mobile number and password are required."
                })
            
            if not mobile.isdigit() or len(mobile) != 10:
                return render(request, "photo_frame/client_signin.html", {
                    "message": "Invalid mobile number. It should be a 10-digit number."
                })

            # Authenticate user
            user = authenticate(username=mobile, password=password)

            if user is not None:
                login(request, user)
                logger.info("User %s logged in successfully.", user.username)
                return redirect("/frame/dashboard")
            else:
                logger.warning("Failed login attempt for mobile: %s", mobile)
                return render(request, "photo_frame/client_signin.html", {
                    "message": "Invalid mobile number or password. Please try again or create an account."
                })
        
        except Exception as e:
            logger.exception("Error during client login: %s", str(e))
            return render(request, "photo_frame/client_error.html", {
                "message": "An unexpected error occurred. Please try again later."
            })

    return render(request, "photo_frame/client_signin.html")


    
def user_logout(request):
    """
    Logs out the user and redirects to the login page.
    """
    try:
        if request.user.is_authenticated:
            username = request.user.username  # Capture username before logout
            logout(request)
            logger.info("User %s logged out successfully.", username)
        else:
            logger.warning("Logout attempted by an unauthenticated user.")

        return redirect("/")  # Redirect to login page after logout

    except Exception as e:
        logger.exception("Error during logout: %s", str(e))
        return redirect("/frame/error")  # Redirect to an error page if an issue occurs
    
@login_required(login_url='/frame/signin')
def add_frame(request, id):
    """
    Handles adding a new frame user along with media for web experience.
    """
    usr = request.user

    try:
        # Get the client or return 404 if not found
        cli_id = get_object_or_404(ClientInfo, id=id)
        framecount = FrameCount.objects.filter(client_id=cli_id).first()
        if not framecount:
            return redirect("/frame/payment")


        if request.method == "POST":
            name = request.POST.get('name')
            email = request.POST.get('emailid')
            contact = request.POST.get('contact')
            video_file = request.FILES.get('videoUpload')
            reference_img = request.FILES.get('refimageUpload')

            

            # Validate required fields
            if not all([name]):
                messages.error(request, "Name are required fields.")
                return redirect(request.path)

            # Save FrameUserInfo
            frame_user = FrameUserInfo.objects.create(
                name=name,
                email=email,
                contact=contact,
                client_id=cli_id
            )
            frame_count_item = FrameCount.objects.filter(client_id=cli_id).first()
            frame_count_item.frame_count = frame_count_item.frame_count - 1
            frame_count_item.save()


            # Save Media if uploaded
            
            if video_file and reference_img:
                MediaForWebExperience.objects.create(user=frame_user, web_video=video_file, reference_img=reference_img)

            logger.info("New frame user '%s' added for client '%s'.", name, cli_id)
            messages.success(request, "Frame user added successfully!")
            return redirect("/frame/dashboard")

    except ValidationError as e:
        logger.error("Validation error: %s", str(e))
        messages.error(request, "Invalid input data. Please check your inputs.")
    except Exception as e:
        logger.exception("Error adding frame user: %s", str(e))
        messages.error(request, "An unexpected error occurred. Please try again.")

    return render(request, "photo_frame/consumer_detail_form.html")

@login_required(login_url='/frame/signin')
def payment(request):
    """
    Handles frame purchase and initiates Razorpay payment order.
    """
    try:
        if request.method == "POST":
            frame_count = int(request.POST.get('count', 10))  # Default to 10 if missing
            if frame_count <= 0:
                return JsonResponse({"error": "Invalid frame count"}, status=400)

            request.session['framecount'] = frame_count

            # ✅ Correct discount logic (highest → lowest)
            if frame_count >= 2000:
                price_per_frame = 0.05
            elif frame_count >= 1000:
                price_per_frame = 0.06
            elif frame_count >= 500:
                price_per_frame = 0.07
            elif frame_count >= 250:
                price_per_frame = 0.08
            elif frame_count >= 100:
                price_per_frame = 0.09
            else:
                price_per_frame = 1

            amount = int(frame_count * price_per_frame * 100)  # convert to paisa
            request.session['fnl_amount'] = amount

            # Create Razorpay Order
            razorpay_order = razorpay_client.order.create({
                "amount": amount,
                "currency": "INR",
                "payment_capture": '0'  
            })

            logger.info(f"Created Razorpay order: {razorpay_order['id']} for {amount} INR")

            return JsonResponse({
                "order_id": razorpay_order["id"],
                "amount": amount,
                "currency": "INR",
                "key": settings.RAZOR_KEY_ID,
                "callback_url": "/frame/paymenthandler/",
            })

    except Exception as e:
        logger.exception("Error in payment processing: %s", str(e))
        return JsonResponse({"error": "Something went wrong. Please try again."}, status=500)

    return render(request, "photo_frame/payment.html")

# @login_required(login_url='/frame/signin')
# def payment(request):
#     """
#     Handles frame purchase and initiates Razorpay payment order.
#     """
#     try:
#         if request.method == "POST":
#             frame_count = int(request.POST.get('count', 10))  # Default to 10 frames if missing
#             if frame_count <= 0:
#                 messages.error(request, "Invalid frame count.")
#                 return JsonResponse({"error": "Invalid frame count"}, status=400)

#             request.session['framecount'] = frame_count
#             amount = (frame_count * 199) * 100  # Convert to paisa
#             request.session['fnl_amount'] = amount

#             # Create Razorpay Order
#             razorpay_order = razorpay_client.order.create({
#                 "amount": amount,
#                 "currency": "INR",
#                 "payment_capture": '0'  # Auto-capture enabled
#             })

#             logger.info(f"Created Razorpay order: {razorpay_order['id']} for {amount} INR")

#             return JsonResponse({
#                 "order_id": razorpay_order["id"],
#                 "amount": amount,
#                 "currency": "INR",
#                 "key": settings.RAZOR_KEY_ID,
#             })

#     except Exception as e:
#         logger.exception("Error in payment processing: %s", str(e))
#         return JsonResponse({"error": "Something went wrong. Please try again."}, status=500)

#     return render(request, "photo_frame/payment.html")

@csrf_exempt
def paymenthandler(request):
    """
    Handles Razorpay payment verification and updates frame count.
    """
    if request.method == "POST":
        try:
            payment_id = request.POST.get('payment_id')
            order_id = request.POST.get('order_id')
            signature = request.POST.get('signature')

            if not all([payment_id, order_id, signature]):
                logger.warning("Missing payment parameters")
                return HttpResponseBadRequest("Missing payment parameters")

            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }

            # Verify Razorpay payment signature
            if not razorpay_client.utility.verify_payment_signature(params_dict):
                logger.error("Payment signature verification failed.")
                return render(request, 'photo_frame/c_paymentfail.html')

            amount = request.session.get('fnl_amount', 0)
            if amount <= 0:
                logger.error("Invalid amount retrieved from session.")
                return render(request, 'photo_frame/c_paymentfail.html')

            # Capture the payment
            razorpay_client.payment.capture(payment_id, amount)
            logger.info(f"Payment captured: {payment_id} for {amount} INR")

            # Update frame count
            count = request.session.get('framecount', 0)
            update_frame_count(request.user, count, payment_id, order_id, amount)

            messages.success(request, "Payment successful! Frames added to your account.")
            return redirect('/frame/dashboard')

        except razorpay.errors.BadRequestError as e:
            logger.exception("Razorpay BadRequestError: %s", str(e))
            return render(request, 'photo_frame/c_paymentfail.html')

        except Exception as e:
            logger.exception("Unexpected error in payment handler: %s", str(e))
            return render(request, 'photo_frame/c_paymentfail.html')

    return HttpResponseBadRequest("Invalid request method")

def update_frame_count(user, count, payment_id, order_id, amount):
    """
    Updates the frame count and logs the payment in the database.
    """
    try:
        client = ClientInfo.objects.filter(user=user).first()
        if not client:
            logger.error("Client not found for user: %s", user)
            return

        frame_count = FrameCount.objects.filter(client_id=client).first()
        if frame_count:
            frame_count.frame_count += count
            frame_count.save()
        else:
            FrameCount.objects.create(client_id=client, frame_count=count)

        # Save payment record
        FramePayment.objects.create(
            client_id=client,
            payment_status=True,
            payment_id=payment_id,
            razorpay_order_id=order_id,
            amount=amount
        )

        logger.info(f"Frame count updated for client {client.id}. Added {count} frames.")

    except Exception as e:
        logger.exception("Error updating frame count: %s", str(e))

def user_experience(request, hasheduserid):
    """
    Retrieves and displays the associated web video for a given user.
    """
   
    try:
        userid = decode_primary_key(hasheduserid)
        frameuser = get_object_or_404(FrameUserInfo, id=userid)

        # Get associated media
        media = MediaForWebExperience.objects.filter(user=frameuser).first()

        if media and media.web_video:
            return render(request, "photo_frame/user_experience.html", {"media": media})

        logger.warning(f"No video found for user {userid}")
        return JsonResponse({"error": "No video found"}, status=404)

    except Exception as e:
        logger.exception("Error in camera_feed: %s", str(e))
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)


def cancellation_policy(request):
    """
    Renders the Privacy Policy page.
    """
    return render(request, "photo_frame/cancellation_policy.html")
