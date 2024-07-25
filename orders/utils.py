import base64
import datetime

import pytz
import requests
from requests.auth import HTTPBasicAuth

from foodOnline_main import settings


def generate_order_number(pk):
    print("PRIMARY KEY", pk)

    nairobi_tz = pytz.timezone('Africa/Nairobi')

    current_datetime = datetime.datetime.now(nairobi_tz).strftime('%Y%m%d%H%M%S')
    print("THIS IS THE CURRENT TIME", current_datetime)
    order_number = current_datetime + str(pk)
    return order_number


def get_mpesa_token(consumer_key, consumer_secret):
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(api_url, auth=HTTPBasicAuth(consumer_key, consumer_secret))
    if response.status_code == 200:
        return response.json().get('access_token')
    return None

def format_phone_number(phone_number):
    if phone_number.startswith('07'):
        return '254' + phone_number[1:]
    elif phone_number.startswith('254'):
        return phone_number
    else:
        # Handle other cases or raise an error
        raise ValueError("Invalid phone number format")

def initiate_stk_push(token, phone_number, amount, account_reference, transaction_desc, callback_url):
    try:
        phone_number = format_phone_number(phone_number)
    except ValueError as e:
        print(str(e))
        return {'errorMessage': str(e)}
    
    # Ensure the amount is an integer
    amount = int(round(amount))
    print("AMOOOOOUNT" , amount)
    
    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    nairobi_tz = pytz.timezone('Africa/Nairobi')
    timestamp = datetime.datetime.now(nairobi_tz).strftime('%Y%m%d%H%M%S')
    shortcode = settings.MPESA_SHORTCODE
    passkey = settings.MPESA_PASSKEY
    password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode('utf-8')

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": shortcode,
        "PhoneNumber": phone_number,
        "CallBackUrl": callback_url,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_desc
    }

    response = requests.post(api_url, json=payload, headers=headers)
    print('Status Code:', response.status_code)
    print('Response:', response.json())

    if response.status_code == 200:
        return response.json()
    else:
        return response.json()