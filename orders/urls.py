from django.urls import path
from . import views

urlpatterns = [
    path('place_order/', views.place_order, name='place_order'),
    path('initiate-stk-push/', views.initiate_stk_push, name='initiate_stk_push'),
    path('mpesa/callback/', views.MpesaCallbackView.as_view(), name='mpesa_callback'),
    path('payments/', views.payments, name='payments'),
    path('order_complete/', views.order_complete, name='order_complete'),
    
]