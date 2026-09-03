from django.urls import path
from .views import (
    mpesa_callback, home, order_detail,order_history, payment_status, add_to_cart, cart_detail, 
    remove_from_cart, update_cart_quantity, checkout, checkout_page, order_success,
    signup_view, login_view, logout_view, profile_view,
    verify_email, resend_verification,
    CustomPasswordResetView, password_reset_done_view,
    CustomPasswordResetConfirmView, password_reset_complete_view,
    location_select_page, save_location, api_get_plots
)

urlpatterns = [
    path('', home, name='home'),
    path('add-to-cart/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('cart/', cart_detail, name='cart_detail'),
    path('remove-from-cart/<int:product_id>/', remove_from_cart, name='remove_from_cart'),
    path(
        'update-cart/<int:product_id>/<str:action>/',
        update_cart_quantity,
        name='update_cart_quantity'
    ),
    path('checkout/', checkout_page, name='checkout_page'),
    path('process-payment/', checkout, name='process_payment'),
    path('order-success/', order_success, name='order_success'),
    path('payment-status/<int:order_id>/', payment_status),
    path('mpesa/callback/', mpesa_callback, name='mpesa_callback'),
    
    # Authentication URLs
    path('signup/', signup_view, name='signup'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    
    # Email Verification URLs
    path('verify-email/<str:token>/', verify_email, name='verify_email'),
    path('resend-verification/', resend_verification, name='resend_verification'),
    
    # Password Reset URLs
    path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', password_reset_done_view, name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         CustomPasswordResetConfirmView.as_view(), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         password_reset_complete_view, 
         name='password_reset_complete'),
    path('select-location/', location_select_page, name='location_select'),
    path('save-location/', save_location, name='save_location'),
    path('api/plots/<int:area_id>/', api_get_plots, name='api_get_plots'),
    path('orders/', order_history, name='order_history'),
    path('orders/<int:order_id>/', order_detail, name='order_detail'),
]