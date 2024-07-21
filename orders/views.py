from django.http import HttpResponse
import simplejson as json
from django.shortcuts import redirect, render

from marketplace.context_processors import get_cart_amounts
from marketplace.models import Cart
from orders.forms import OrderForm
from orders.models import Order, Payment
from orders.utils import generate_order_number

# Create your views here.

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

        #  send order confirmation email to the customer

        #  send the order received email to the vendor

        # clear the cart if the payment is success

        # return back to ajax with the status success or failure
    return HttpResponse('Payments View')