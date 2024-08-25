import base64
import datetime
import simplejson as json

import pytz
import requests
from requests.auth import HTTPBasicAuth

from foodOnline_main import settings


def generate_order_number(pk):
    nairobi_tz = pytz.timezone('Africa/Nairobi')
    current_datetime = datetime.datetime.now(nairobi_tz).strftime('%Y%m%d%H%M%S')
    order_number = current_datetime + str(pk)
    return order_number

def order_total_by_vendor(order, vendor_id):
    total_data = json.loads(order.total_data)
    data = total_data.get(str(vendor_id))

    subtotal = 0
    tax = 0
    tax_dict = {}

    for key, val in data.items():
        subtotal += float(key)
        val = val.replace("'", '"')
        val = json.loads(val)
        tax_dict.update(val)
        
        # calculate tax
        for i in val:
            for j in val[i]:
                tax += float(val[i][j])
    grand_total = float(subtotal) + float(tax)

        
        # print("subtotal : ", subtotal)
        # print("tax : ", tax)
        # print("tax_dict : ", tax_dict)
        # print("grand_total : ", grand_total)

    context = {
        'subtotal' : subtotal,
        'tax_dict' : tax_dict,
        'grand_total' : grand_total,
    }

    return context

def get_mpesa_token(consumer_key, consumer_secret):
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(api_url, auth=HTTPBasicAuth(consumer_key, consumer_secret))
    print("RESPONSE FOR ACCESS TOKEN", response)
    if response.status_code == 200:
        print("STATUS CODE ACCESS TOKEN", response.status_code)
        print('THIS IS IT', response.json().get('access_token'))
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
