import base64
import datetime
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.views import View
import pytz
import requests
import simplejson as json
from django.shortcuts import get_object_or_404, redirect, render

from foodOnline_main import settings
from marketplace.context_processors import get_cart_amounts
from marketplace.models import Cart, Tax
from menu.models import FoodItem
from orders.forms import OrderForm
from orders.models import Order, OrderedFood, Payment
from orders.utils import generate_order_number, get_mpesa_token, order_total_by_vendor

from accounts.utils import send_notification
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from requests.auth import HTTPBasicAuth
import logging
from django.contrib.sites.shortcuts import get_current_site
# Create your views here.


@login_required(login_url='login')
def place_order(request):
    cart_items = Cart.objects.filter(user = request.user).order_by('created_at')
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('marketplace')
    
    vendors_ids = []
    for i in cart_items:
        if i.fooditem.vendor.id not in vendors_ids:
            vendors_ids.append(i.fooditem.vendor.id)
    
    get_tax = Tax.objects.filter(is_active = True)
    subtotal = 0
    total_data = {}
    k = {}
    for i in cart_items:
        fooditem = FoodItem.objects.get(pk = i.fooditem.id, vendor_id__in = vendors_ids)
        v_id = fooditem.vendor.id
        if v_id in k:
            subtotal = k[v_id]
            subtotal += (fooditem.price * i.quantity)
            k[v_id] = subtotal
        else:
            subtotal = (fooditem.price * i.quantity)
            k[v_id] = subtotal

        # Calculate the tax_data
        tax_dict = {}
        for i in get_tax:
            tax_type = i.tax_type
            tax_percentage = i.tax_percentage
            tax_amount = round((tax_percentage * subtotal)/100, 2)
            tax_dict.update({tax_type: {str(tax_percentage) : str(tax_amount)}})
    
        # construct total data
        total_data.update({fooditem.vendor.id : {str(subtotal) : str(tax_dict)}})
    print("TOTAL DATA: ", total_data)


    subtotal = get_cart_amounts(request)['subtotal']
    total_tax = get_cart_amounts(request)['tax']
    grand_total = get_cart_amounts(request)['grand_total']
    tax_data = get_cart_amounts(request)['tax_dict']

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = Order()
            order.first_name = form.cleaned_data['first_name']
            order.last_name = form.cleaned_data['last_name']
            order.phone = form.cleaned_data['phone']
            order.email = form.cleaned_data['email']
            order.address = form.cleaned_data['address']
            order.country = form.cleaned_data['country']
            order.state = form.cleaned_data['state']
            order.city = form.cleaned_data['city']
            order.pin_code = form.cleaned_data['pin_code']

            order.user = request.user
            order.total = grand_total
            order.tax_data = json.dumps(tax_data)
            order.total_data = json.dumps(total_data)
            order.total_tax = total_tax
            order.payment_method = request.POST['payment_method']
            order.save() # Order id/pk is generated
            order.order_number = generate_order_number(order.id)
            order.vendors.add(*vendors_ids)
            order.save()

            context = {
                'order' : order,
                'cart_items': cart_items,
            }
            return render(request, 'orders/place_order.html' , context)

        else:
            print(form.errors)

    return render(request, 'orders/place_order.html')

@login_required(login_url='login')
def payments(request):
    # Check if the request is ajax or not
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'POST':
        #  store the payment details in the payment model
        order_number = request.POST.get('order_number')
        transaction_id = request.POST.get('transaction_id')
        payment_method = request.POST.get('payment_method')
        status = request.POST.get('status')

        order = Order.objects.get(user= request.user, order_number= order_number)
        payment = Payment(
            user = request.user,
            transaction_id = transaction_id,
            payment_method = payment_method,
            amount = order.total,
            status = status
        )
        payment.save()

        # update the order model
        order.payment = payment
        order.is_ordered = True
        order.save()
    
        #  move the cart items to ordered food model
        cart_items = Cart.objects.filter(user = request.user)
        for item in cart_items:
            ordered_food = OrderedFood()
            ordered_food.order = order
            ordered_food.payment = payment
            ordered_food.user = request.user
            ordered_food.fooditem = item.fooditem
            ordered_food.quantity = item.quantity
            ordered_food.price = item.fooditem.price
            ordered_food.amount = item.fooditem.price * item.quantity # total amount
            ordered_food.save()

        #  send order confirmation email to the customer
        mail_subject ='Thank you for ordering with us.'
        mail_template = 'orders/order_confirmation_email.html'
        ordered_food = OrderedFood.objects.filter(order =order)
        customer_subtotal = 0
        for item in ordered_food:
            customer_subtotal += (item.price * item.quantity)
        tax_data = json.loads(order.tax_data)
        context = {
            'user':  request.user,
            'order':order,
            'to_email':order.email,
            'ordered_food' : ordered_food,
            'domain' : get_current_site(request),
            'customer_subtotal' : customer_subtotal,
            'tax_data': tax_data,
        }
        send_notification(mail_subject, mail_template, context)

        #  send the order received email to the vendor
        mail_subject = 'You have received a new order.'
        mail_template = 'orders/new_order_received.html'
        to_emails = []
        for i in cart_items:
            if i.fooditem.vendor.user.email not in to_emails:
                to_emails.append(i.fooditem.vendor.user.email)

                ordered_food_to_vendor = OrderedFood.objects.filter(order =order, fooditem__vendor = i.fooditem.vendor)
                
                
                context = {
                    'order': order,
                    'to_email': i.fooditem.vendor.user.email,
                    'ordered_food_to_vendor' : ordered_food_to_vendor,
                    'vendor_subtotal': order_total_by_vendor(order, i.fooditem.vendor.id)['subtotal'],
                    'tax_data' : order_total_by_vendor(order, i.fooditem.vendor.id)['tax_dict'],
                    'vendor_grand_total' : order_total_by_vendor(order, i.fooditem.vendor.id)['grand_total'],
                    
                }
                send_notification(mail_subject, mail_template, context)

        # clear the cart if the payment is success
        # cart_items.delete()

        # return back to ajax with the status success or failure
        response = {
            'order_number' :order_number,
            'transaction_id': transaction_id,
        }
        return JsonResponse (response)
    return HttpResponse('Payments View')

@login_required(login_url='login')
def order_complete(request):
    order_number = request.GET.get('order_no')
    transaction_id = request.GET.get('trans_id')
    try:
        order = Order.objects.get(order_number = order_number, payment__transaction_id = transaction_id, is_ordered= True)
        ordered_food = OrderedFood.objects.filter(order = order)
        subtotal = 0
        for item in ordered_food:
            subtotal += (item.price * item.quantity)
        tax_data = json.loads(order.tax_data)
        context = {
            'order':order,
            'ordered_food':ordered_food,
            'subtotal': subtotal,
            'tax_data': tax_data,
        }
        return render(request, 'orders/order_complete.html', context)
    except:
        return redirect ('home')

logger = logging.getLogger(__name__)




@login_required(login_url='login')
def initiate_stk_push(request):
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        order_number = request.POST.get('order_number')
        phone_number = request.POST.get('phone_number')
        
        formatted_phone_number = format_phone_number(phone_number)
        print('Formatted Phone Number:', formatted_phone_number)

        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        amount = int(order.total)

        # Generate the password
        shortcode = settings.MPESA_SHORTCODE
        passkey = settings.MPESA_PASSKEY
        nairobi_tz = pytz.timezone('Africa/Nairobi')
        timestamp = datetime.datetime.now(nairobi_tz).strftime('%Y%m%d%H%M%S')
        
        data_to_encode = shortcode + passkey + timestamp
        password = base64.b64encode(data_to_encode.encode()).decode('utf-8')

        api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        
        callback_url = "https://9eab-169-150-218-77.ngrok-free.app/callbackurl"
        print('Callback URL:', callback_url)

        # Get the access token
        access_token = get_mpesa_token(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET)
        print('Access Token:', access_token)
        
        # Make the STK push request
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }

        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerBuyGoodsOnline",
            "Amount": amount,
            "PartyA": formatted_phone_number,
            "PartyB": shortcode,
            "PhoneNumber": formatted_phone_number,
            "CallBackURL": callback_url,
            "AccountReference": order_number,
            "TransactionDesc": 'Payment for order ' + order_number
        }

        print('Payload:', payload)  

        response = requests.post(
            api_url,
            json=payload,
            headers=headers
        )

        response_data = response.json()
        print('Response Data:', response_data)

        if response.status_code == 200:
            return JsonResponse(response_data)
        else:
            return JsonResponse({'error': 'Failed to initiate STK Push', 'details': response_data}, status=response.status_code)

    return JsonResponse({'error': 'Invalid request'}, status=400)

def format_phone_number(phone_number):
    if phone_number.startswith('07'):
        return '254' + phone_number[1:]
    elif phone_number.startswith('254'):
        return phone_number
    else:
        raise ValueError("Invalid phone number format")


@csrf_exempt
@require_POST
def callbackurl(request):
    try:
        # Parse the JSON data posted to the callback URL
        mpesa_response = json.loads(request.body)

        # Log the response to a file
        log_file = "M_PESAConfirmationResponse.txt"
        with open(log_file, "a") as log:
            log.write(json.dumps(mpesa_response) + "\n")

        print(mpesa_response)

        # Extract the ResultCode
        result_code = mpesa_response['Body']['stkCallback']['ResultCode']
        #
        # if result_code == 0:
        #     # Extract additional information from the CallbackMetadata
        #     callback_metadata = mpesa_response['Body']['stkCallback']['CallbackMetadata']['Item']
        #
        #     # Initialize variables to store the extracted data
        #     mpesa_receipt_number = transaction_date = phone_number = amount = None
        #
        #     # Iterate through the metadata to extract the required fields
        #     for item in callback_metadata:
        #         if item['Name'] == 'MpesaReceiptNumber':
        #             mpesa_receipt_number = item['Value']
        #         elif item['Name'] == 'TransactionDate':
        #             transaction_date = item['Value']
        #         elif item['Name'] == 'PhoneNumber':
        #             phone_number = item['Value']
        #         elif item['Name'] == 'Amount':
        #             amount = item['Value']
        #
        #     # Print the extracted values
        #     print("MpesaReceiptNumber:", mpesa_receipt_number)
        #     print("TransactionDate:", transaction_date)
        #     print("PhoneNumber:", phone_number)
        #     print("Amount:", amount)
        #
        #     # Return the success response
        #     response = {
        #         "ResultCode": 0,
        #         "ResultDesc": "Confirmation Received Successfully"
        #     }
        #     print(response)

        #     return JsonResponse({"message": "Response received"}, status=200)
        # else:
        #     # Return a response indicating that the transaction failed
        #     response = {
        #         "ResultCode": result_code,
        #         "ResultDesc": "Transaction failed"
        #     }
        #     print(response)
        #     return JsonResponse(response, status=400)
        return JsonResponse({"message": "Response received"}, status=200)

    except json.JSONDecodeError:
        print("Invalid JSON data")
        return JsonResponse({"message": "Invalid JSON data"}, status=400)
    except KeyError as e:
        print(f"Missing key in JSON data: {e}")
        return JsonResponse({"message": f"Missing key in JSON data: {e}"}, status=400)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)
 