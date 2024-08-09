import simplejson as json
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from accounts.forms import UserInfoForm, UserProfileForm
from accounts.models import UserProfile
from orders.models import Order, OrderedFood
from django.core.paginator import Paginator

# Create your views here.


@login_required(login_url='login')
def cprofile(request):
    profile = get_object_or_404(UserProfile, user = request.user)
    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance = profile)
        user_form = UserInfoForm(request.POST, instance=request.user)
        if profile_form.is_valid() and user_form.is_valid():
            profile_form.save()
            user_form.save()
            messages.success(request, 'Profile updates')
            return redirect('cprofile')
        else:
            print(profile_form.errors)
            print(user_form.errors)

    else:
        profile_form = UserProfileForm(instance = profile)
        user_form = UserInfoForm(instance = request.user)


    context = {
        'profile_form': profile_form,
        'user_form' : user_form,
        'profile': profile,
    }
    return render(request,  'customers/cprofile.html', context)


def my_orders(request):
    orders_list = Order.objects.filter(user=request.user, is_ordered= True).order_by('-created_at')
    # Pagination
    per_page = request.GET.get('per_page', 10)
    page_number = request.GET.get('page', 1)
    paginator = Paginator(orders_list, per_page)
    orders = paginator.get_page(page_number)

    context = {
        'orders' : orders,
        'order_count': orders_list.count(),
        'per_page_options': [5,10,20,50],
        'selected_per_page': per_page
    }
    return render(request, 'customers/my_orders.html', context)


def order_detail(request, order_number):
    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_food= OrderedFood.objects.filter(order= order)
        subtotal = 0
        for item in ordered_food:
            subtotal +=  (item.price * item.quantity) 
        tax_data = json.loads(order.tax_data)
        context = {
            'order': order,
            'ordered_food': ordered_food,
            'subtotal': subtotal,
            'tax_data': tax_data,
        }
        return render(request, 'customers/order_detail.html', context)
    except:
        return redirect('customer')