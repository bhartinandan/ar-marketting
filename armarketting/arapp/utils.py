import requests
import base64
import json
from datetime import datetime
import qrcode
import qrcode
from PIL import Image

def token():
    key="Mydearstreeya"
    encoded_key = base64.b64encode(key.encode('utf-8')).decode('utf-8')
    url = f"https://cpaas.messagecentral.com/auth/v1/authentication/token?customerId=C-C8BD832A802347A&key={encoded_key}&scope=NEW&country=91"

    payload = {}
    headers = {
    'accept': '*/*'
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    print(response.text)
    return json.loads(response.text)

def send_phone_otp(phone_no,aut):
        
    url = f"https://cpaas.messagecentral.com/verification/v3/send?countryCode=91&customerId=C-C8BD832A802347A&flowType=SMS&mobileNumber={phone_no}"
    # url = "https://cpaas.messagecentral.com/verification/v3/send?countryCode=91&flowType=SMS&mobileNumber=7319847865"

    payload = {}
    headers = {
    'authToken': aut
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)
    return json.loads(response.text)

# print(otp("7319847865"))


def verify_otp(phone_no,otp,ver_code,aut):
    # phone_no=str(phone_no)
    # otp=str(otp)
    # ver_code=str(ver_code)
    print("auth token", aut)

    url = f"https://cpaas.messagecentral.com/verification/v3/validateOtp?countryCode=91&mobileNumber={phone_no}&verificationId={ver_code}&customerId=C-C8BD832A802347A&code={otp}"

    payload = {}
    headers = {
    'authToken': aut
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    print(response.text)

    return json.loads(response.text)

def send_email(email, subject, message):
    url = "https://api.sendinblue.com/v3/smtp/email"

    payload = json.dumps({
        "sender": {
            "name": "Armarketting",
            "email": ""
        },
        "to": [
            {
                "email": email,
                "name": "Armarketting"
            }
        ],  })

from hashids import Hashids

hashids = Hashids(salt="lets_go_to_mountain", min_length=8)  # Add a salt for security

def encode_primary_key(pk: int) -> str:
    return hashids.encode(pk)

def decode_primary_key(hashid: str) -> int:
    return hashids.decode(hashid)[0] if hashids.decode(hashid) else None

# Example usage

import qrcode
from PIL import Image
#designer qr
def designer_qr():

    import qrcode
    from PIL import Image, ImageDraw
    
    # Data for QR
    # data = "https://aliveframe.com/view-3d-model/p2lwYO08"
    data = "https://4d28-2401-9640-1003-8afd-18b4-efed-ec1d-5f15.ngrok-free.app/loyalty/customer-dashboard/p2lwYO08"

    # Create QR
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=2
    )

    qr.add_data(data)
    qr.make(fit=True)

    # White background QR
    qr_img = qr.make_image(
        fill_color="black",
        back_color="white"
    ).convert("RGBA")

    # Load Logo
    logo = Image.open("aliveframe_logo.png").convert("RGBA")

    # Resize logo
    logo_size = int(qr_img.size[0] / 4)
    logo = logo.resize((logo_size, logo_size))

    # Create white background for logo
    padding = 20
    white_bg_size = logo_size + padding

    white_bg = Image.new(
        "RGBA",
        (white_bg_size, white_bg_size),
        (255, 255, 255, 255)
    )

    # Optional: Rounded corners
    mask = Image.new("L", (white_bg_size, white_bg_size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        (0, 0, white_bg_size, white_bg_size),
        radius=20,
        fill=255
    )
    white_bg.putalpha(mask)

    # Paste logo on white bg
    logo_pos = (
        (white_bg_size - logo_size) // 2,
        (white_bg_size - logo_size) // 2
    )

    white_bg.paste(logo, logo_pos, logo)

    # Center position
    pos = (
        (qr_img.size[0] - white_bg_size) // 2,
        (qr_img.size[1] - white_bg_size) // 2
    )

    # Paste white bg on QR
    qr_img.paste(white_bg, pos, white_bg)

    # Save
    qr_img.save("designer_qr.png")

    print("Professional Designer QR Created")


def main():
    print("Hello, this is the main function!")

if __name__ == "__main__":

    hashed_id = encode_primary_key(8)
    print(hashed_id)  # Example: 'x9J3yK8d'

    

    # Data you want inside QR
    # data = "https://aliveframe.com/ar-game-landing/pBlENkjY"
    data = "https://aliveframe.com/view-3d-model/45kmGngd"

    # Create QR
    qr = qrcode.QRCode(
        version=1,  # controls size (1 = small, 40 = large)
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )

    qr.add_data(data)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    print(img)

    # Save image
    img.save("qrcode.png")

    # designer_qr()

    print("QR Code generated successfully!")

    

    original_id = decode_primary_key("p2lwYO08")
    print(original_id)  # Output: 123
    


