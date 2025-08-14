import requests
import base64
import json
from datetime import datetime

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


from hashids import Hashids

hashids = Hashids(salt="lets_go_to_mountain", min_length=8)  # Add a salt for security

def encode_primary_key(pk: int) -> str:
    return hashids.encode(pk)

def decode_primary_key(hashid: str) -> int:
    return hashids.decode(hashid)[0] if hashids.decode(hashid) else None

# Example usage



def main():
    print("Hello, this is the main function!")

if __name__ == "__main__":
    hashed_id = encode_primary_key(12)
    print(hashed_id)  # Example: 'x9J3yK8d'

    original_id = decode_primary_key("Q6ley8lJ")
    print(original_id)  # Output: 123
    


