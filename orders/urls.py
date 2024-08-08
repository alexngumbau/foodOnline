from django.urls import path
from . import views

urlpatterns = [
    path('place_order/', views.place_order, name='place_order'),
    path('initiate-stk-push/', views.initiate_stk_push, name='initiate_stk_push'),
    path('callbackurl/', views.callbackurl, name='callbackurl'),
    path('payments/', views.payments, name='payments'),
    path('order_complete/', views.order_complete, name='order_complete'),
    
]
