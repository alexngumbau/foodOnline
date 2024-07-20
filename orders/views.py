from django.shortcuts import redirect, render

# Create your views here.

def place_order(request):
    return render(request, 'orders/place_order.html')