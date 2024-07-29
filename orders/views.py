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
from marketplace.models import Cart
from orders.forms import OrderForm
from orders.models import Order, OrderedFood, Payment
from orders.utils import generate_order_number, get_mpesa_token

from accounts.utils import send_notification
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from requests.auth import HTTPBasicAuth
import logging
# Create your views here.


@login_required(login_url='login')
def place_order(request):
    cart_items = Cart.objects.filter(user = request.user).order_by('created_at')
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('marketplace')
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
            order.total_tax = total_tax
            order.payment_method = request.POST['payment_method']
            order.save() # Order id/pk is generated
            order.order_number = generate_order_number(order.id)
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
        context = {
            'user':  request.user,
            'order':order,
            'to_email':order.email,
        }
        send_notification(mail_subject, mail_template, context)

        #  send the order received email to the vendor
        mail_subject = 'You have received a new order.'
        mail_template = 'orders/new_order_received.html'
        to_emails = []
        for i in cart_items:
            if i.fooditem.vendor.user.email not in to_emails:
                to_emails.append(i.fooditem.vendor.user.email)

        context = {
            'order': order,
            'to_email': to_emails,
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
        
        callback_url = "https://270d-102-213-49-40.ngrok-free.app/callbackurl"
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


