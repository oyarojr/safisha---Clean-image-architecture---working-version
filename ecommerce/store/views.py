from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Category, Order, OrderItem, Cart, CartItem
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from .utils import send_whatsapp_message, initiate_stk_push, format_phone
from .models import Order, OrderItem, MpesaTransaction
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
from django.db.models import Prefetch, Q
from django.db import transaction
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .forms import SignupForm, UserUpdateForm, ProfileUpdateForm
from django.contrib import messages
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
from .utils import send_verification_email, generate_verification_token
from .models import Profile
from .forms import CustomPasswordResetForm, CustomSetPasswordForm
from django.http import JsonResponse
from .models import MainArea, Plot, PlotImage
import cloudinary.utils 

# Create your views here.
@login_required(login_url='/login/')
def location_select_page(request):
    """
    Location selection page - shown after signup or when updating location
    """
    main_areas = MainArea.objects.filter(is_active=True).prefetch_related('plots')
    
    context = {
        'main_areas': main_areas,
    }
    
    return render(request, 'store/location_select.html', context)


@login_required(login_url='/login/')
def save_location(request):
    """
    Save selected plot to user profile
    """
    if request.method == 'POST':
        plot_id = request.POST.get('plot_id')
        
        try:
            plot = Plot.objects.get(id=plot_id, is_active=True)
            profile = request.user.profile
            profile.default_plot = plot
            profile.location_setup_complete = True
            profile.save()
            
            messages.success(request, f'Location saved! Deliveries will be sent to {plot.name}')
            
            # Redirect to home or wherever they were going
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
            
        except Plot.DoesNotExist:
            messages.error(request, 'Invalid plot selected')
            return redirect('location_select')
    
    return redirect('location_select')




def api_get_plots(request, area_id):
    try:
        area = MainArea.objects.get(id=area_id, is_active=True)
        plots = Plot.objects.filter(
            main_area=area,
            is_active=True
        ).prefetch_related('images')

        plots_data = []
        for plot in plots:
            primary_image = plot.get_primary_image()
            all_images = [
                cloudinary.utils.cloudinary_url(
                    str(img.image), format='jpg', secure=True
                )[0]
                for img in plot.images.all()
            ]

            plots_data.append({
                'id': plot.id,
                'name': plot.name,
                'description': plot.description,
                'landmark_description': plot.landmark_description,
                'primary_image': cloudinary.utils.cloudinary_url(
                    str(primary_image.image), format='jpg', secure=True
                )[0] if primary_image else None,
                'images': all_images,
                'image_count': len(all_images),
            })

        return JsonResponse(plots_data, safe=False)

    except MainArea.DoesNotExist:
        return JsonResponse({'error': 'Area not found'}, status=404)

# Helper function to get cart data
def get_cart_data(request):
    """Get cart items and count for both authenticated and anonymous users"""
    if request.user.is_authenticated:
        # Get or create cart for authenticated user
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.select_related('product').all()
        cart_count = cart.get_total_items()
        
        # Convert to dictionary format for consistency
        cart_dict = {}
        for item in cart_items:
            cart_dict[str(item.product.id)] = {
                'quantity': item.quantity
            }
        return cart_dict, cart_count
    else:
        # Use session for anonymous users
        cart = request.session.get('cart', {})
        cart_count = sum(item['quantity'] for item in cart.values())
        return cart, cart_count


def merge_session_cart_to_db(request):
    """Merge session cart to database cart when user logs in"""
    if not request.user.is_authenticated:
        return
    
    session_cart = request.session.get('cart', {})
    if not session_cart:
        return
    
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    for product_id, item in session_cart.items():
        try:
            product = Product.objects.get(id=product_id)
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': item['quantity']}
            )
            if not created:
                # Add to existing quantity
                cart_item.quantity += item['quantity']
                cart_item.save()
        except Product.DoesNotExist:
            continue
    
    # Clear session cart after merging
    request.session.pop('cart', None)
    request.session.modified = True


def home(request):
    query = request.GET.get('q', '').strip()

    product_filter = Q()
    if query:
        product_filter = (
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    filtered_products = Product.objects.filter(product_filter)
    has_results = filtered_products.exists()

    categories = Category.objects.prefetch_related(
        Prefetch(
            'products',
            queryset=filtered_products,
            to_attr='filtered_products'
        )
    )

    cart, cart_count = get_cart_data(request)

    return render(request, 'store/home.html', {
        'categories': categories,
        'query': query,
        'cart_count': cart_count,
        'has_results': has_results,
    })
    

def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Send verification email
            try:
                send_verification_email(user, request)
                messages.success(
                    request, 
                    "Account created! Please check your email to verify your account."
                )
            except Exception as e:
                messages.warning(
                    request,
                    "Account created but verification email failed to send. "
                    "You can resend it from your profile."
                )
            
            login(request, user)
            
            # Merge session cart to database
            merge_session_cart_to_db(request)
            
            return redirect('home')
    else:
        form = SignupForm()

    return render(request, 'store/signup.html', {'form': form})


def login_view(request):
    next_url = request.GET.get('next', 'home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            
            # Merge session cart to database
            merge_session_cart_to_db(request)
            
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'store/login.html', {'next': next_url})


def logout_view(request):
    logout(request)
    return redirect('home')


def add_to_cart(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)

        if request.user.is_authenticated:
            # Handle authenticated user - use database
            cart, created = Cart.objects.get_or_create(user=request.user)
            
            try:
                cart_item = CartItem.objects.get(cart=cart, product=product)
                current_qty = cart_item.quantity
                
                if current_qty >= product.stock_quantity:
                    return JsonResponse({
                        'success': False,
                        'error': 'Not enough stock available'
                    }, status=400)
                
                cart_item.quantity += 1
                cart_item.save()
            except CartItem.DoesNotExist:
                if product.stock_quantity < 1:
                    return JsonResponse({
                        'success': False,
                        'error': 'Not enough stock available'
                    }, status=400)
                
                CartItem.objects.create(
                    cart=cart,
                    product=product,
                    quantity=1
                )
            
            cart_count = cart.get_total_items()
        else:
            # Handle anonymous user - use session
            cart = request.session.get('cart', {})

            current_qty = cart.get(str(product_id), {}).get('quantity', 0)

            if current_qty >= product.stock_quantity:
                return JsonResponse({
                    'success': False,
                    'error': 'Not enough stock available'
                }, status=400)

            if str(product_id) in cart:
                cart[str(product_id)]['quantity'] += 1
            else:
                cart[str(product_id)] = {'quantity': 1}

            request.session['cart'] = cart
            request.session.modified = True
            
            cart_count = sum(item['quantity'] for item in cart.values())

        return JsonResponse({
            'success': True,
            'cart_count': cart_count
        })


def cart_detail(request):
    if request.user.is_authenticated:
        # Get cart from database
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items_db = cart.items.select_related('product').all()
        
        cart_items = []
        total_price = 0
        
        for item in cart_items_db:
            subtotal = item.product.price * item.quantity
            cart_items.append({
                'product': item.product,
                'quantity': item.quantity,
                'subtotal': subtotal
            })
            total_price += subtotal
    else:
        # Get cart from session
        cart = request.session.get('cart', {})
        cart_items = []
        total_price = 0

        for product_id, item in cart.items():
            product = get_object_or_404(Product, id=product_id)
            quantity = item['quantity']
            subtotal = product.price * quantity

            cart_items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })

            total_price += subtotal

    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total_price': total_price
    })


def remove_from_cart(request, product_id):
    if request.user.is_authenticated:
        # Remove from database
        cart = get_object_or_404(Cart, user=request.user)
        try:
            cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
            cart_item.delete()
        except CartItem.DoesNotExist:
            pass
    else:
        # Remove from session
        cart = request.session.get('cart', {})

        if str(product_id) in cart:
            del cart[str(product_id)]
            request.session['cart'] = cart
            request.session.modified = True

    return redirect('cart_detail')


def update_cart_quantity(request, product_id, action):
    if request.user.is_authenticated:
        # Update in database
        cart = get_object_or_404(Cart, user=request.user)
        try:
            cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
            
            if action == 'increase':
                # Check stock before increasing
                if cart_item.quantity < cart_item.product.stock_quantity:
                    cart_item.quantity += 1
                    cart_item.save()
            elif action == 'decrease':
                cart_item.quantity -= 1
                if cart_item.quantity <= 0:
                    cart_item.delete()
                else:
                    cart_item.save()
        except CartItem.DoesNotExist:
            pass
    else:
        # Update in session
        cart = request.session.get('cart', {})

        if str(product_id) in cart:
            if action == 'increase':
                cart[str(product_id)]['quantity'] += 1
            elif action == 'decrease':
                cart[str(product_id)]['quantity'] -= 1

                if cart[str(product_id)]['quantity'] <= 0:
                    del cart[str(product_id)]

        request.session['cart'] = cart
        request.session.modified = True

    return redirect('cart_detail')


@login_required(login_url='/login/')
def checkout_page(request):
    """Display checkout page with delivery options"""
    profile = request.user.profile
    
    # Check if user has set their location
    if not profile.location_setup_complete or not profile.default_plot:
        messages.info(request, 'Please select your delivery location first')
        return redirect('location_select')
    
    cart = get_object_or_404(Cart, user=request.user)
    cart_items_db = cart.items.select_related('product').all()
    
    if not cart_items_db:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart_detail')
    
    cart_items = []
    total_price = Decimal('0')
    
    for item in cart_items_db:
        subtotal = item.product.price * item.quantity
        
        cart_items.append({
            'product': item.product,
            'quantity': item.quantity,
            'subtotal': subtotal
        })
        
        total_price += subtotal
    
    # Get user's default plot and area
    default_plot = profile.default_plot
    delivery_fee = default_plot.main_area.delivery_fee
    
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'default_plot': default_plot,
        'delivery_fee': delivery_fee,
        'grand_total': total_price + delivery_fee,
    }
    
    return render(request, 'store/checkout.html', context)


@login_required(login_url='/login/')
def checkout(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')
        # Get plot_id from either form or user's default
        plot_id = request.POST.get('plot_id')
        
        if not plot_id:
            plot = request.user.profile.default_plot
        else:
            plot = get_object_or_404(Plot, id=plot_id)
        
        if not plot:
            return JsonResponse({
                'error': 'No delivery location selected'
            }, status=400)
        
        delivery_fee = plot.main_area.delivery_fee
        phone = format_phone(phone)

        cart = get_object_or_404(Cart, user=request.user)
        cart_items_db = cart.items.select_related('product').all()

        if not cart_items_db:
            return JsonResponse({
                'error': 'Your cart is empty'
            }, status=400)

        # Calculate total
        with transaction.atomic():
            total = Decimal('0')
            for item in cart_items_db:
                product = item.product
                if product.stock_quantity < item.quantity:
                    return JsonResponse({
                        'error': f"Not enough stock for {product.name}"
                    }, status=400)
                total += product.price * item.quantity

            total_amount = total + delivery_fee

            order = Order.objects.create(
                user=request.user,
                plot=plot,
                location=f"{plot.name}, {plot.main_area.name}",  # Keep for backward compatibility
                delivery_fee=delivery_fee,
                total_amount=total_amount,
                is_paid=False
            )

            for item in cart_items_db:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price
                )

            mpesa_txn = MpesaTransaction.objects.create(
                order=order,
                phone_number=phone
            )

        response = initiate_stk_push(phone, total_amount, order.id)

        mpesa_txn.checkout_request_id = response.get('CheckoutRequestID')
        mpesa_txn.merchant_request_id = response.get('MerchantRequestID')
        mpesa_txn.save()

        return JsonResponse({
            'order_id': order.id,
            'checkout_request_id': mpesa_txn.checkout_request_id
        })


@csrf_exempt
def mpesa_callback(request):
    print("🔥 MPESA CALLBACK RECEIVED 🔥")
    print(request.body)

    data = json.loads(request.body)

    stk = data['Body']['stkCallback']
    checkout_id = stk['CheckoutRequestID']

    txn = MpesaTransaction.objects.get(checkout_request_id=checkout_id)

    txn.result_code = stk['ResultCode']
    txn.result_desc = stk['ResultDesc']

    if stk['ResultCode'] == 0:
        items = stk['CallbackMetadata']['Item']
        for item in items:
            if item['Name'] == 'MpesaReceiptNumber':
                txn.mpesa_receipt_number = item['Value']

        txn.status = 'SUCCESS'
        txn.order.is_paid = True
        for item in txn.order.items.all():
            product = item.product
            product.stock_quantity -= item.quantity
            product.save()

        txn.order.save()

        # Clear user's cart after successful payment
        if txn.order.user:
            try:
                cart = Cart.objects.get(user=txn.order.user)
                cart.items.all().delete()
            except Cart.DoesNotExist:
                pass

        # Send WhatsApp + Email
        customer_name = txn.order.user.first_name if txn.order.user else "Unknown"

        # Build WhatsApp message with order items
        order_items = txn.order.items.all()
        items_summary = "\n".join([
            f"{item.product.name} x{item.quantity}"
            for item in order_items
        ])
        
        send_whatsapp_message(
            f"🧾 NEW PAID ORDER\n\n"
            f"Order #: {txn.order.id}\n"
            f"Customer: {customer_name}\n"
            f"Phone: {txn.phone_number}\n\n"
            f"ITEMS:\n{items_summary}\n\n"
            f"Amount: KES {txn.order.total_amount}\n"
            f"Receipt: {txn.mpesa_receipt_number}\n"
            f"Delivery: {txn.order.get_delivery_location()}",
            '254115745813'  # Your WhatsApp number
        )
        

        # Build comprehensive email with order details
        user = txn.order.user
        customer_full_name = f"{user.first_name} {user.last_name}".strip() if user.last_name else customer_name
        customer_email = user.email if user else "N/A"
        
        # Get all order items
        order_items = txn.order.items.all()
        items_text = "\n".join([
            f"  • {item.product.name} x{item.quantity} @ KES {item.price} = KES {item.price * item.quantity}"
            for item in order_items
        ])
        
        # Calculate subtotal (total - delivery fee)
        subtotal = txn.order.total_amount - txn.order.delivery_fee
        
        email_message = f"""
🎉 NEW PAID ORDER RECEIVED!

========================================
ORDER DETAILS
========================================
Order ID: #{txn.order.id}
Order Date: {txn.order.created_at.strftime('%B %d, %Y at %I:%M %p')}
Status: PAID ✅

========================================
CUSTOMER INFORMATION
========================================
Name: {customer_full_name}
Email: {customer_email}
Phone: {txn.phone_number}

========================================
ORDER ITEMS
========================================
{items_text}

========================================
PAYMENT SUMMARY
========================================
Subtotal:        KES {subtotal:.2f}
Delivery Fee:    KES {txn.order.delivery_fee:.2f}
----------------------------------------
TOTAL PAID:      KES {txn.order.total_amount:.2f}

M-Pesa Receipt:  {txn.mpesa_receipt_number}

========================================
DELIVERY INFORMATION
========================================
Location: {txn.order.get_delivery_location()}
Expected: 30-60 minutes

========================================

Please prepare this order for delivery.

MyStore Team
"""
        
        send_mail(
            subject=f"🧾 NEW ORDER #{txn.order.id} - KES {txn.order.total_amount} PAID",
            message=email_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=["oyarodaniel740@gmail.com"],
            fail_silently=False,
        )

        # Send order confirmation email to customer
        if user and customer_email != "N/A":
            customer_email_message = f"""
Dear {customer_full_name},

Thank you for your order! Your payment has been successfully processed.

========================================
ORDER CONFIRMATION
========================================
Order ID: #{txn.order.id}
Order Date: {txn.order.created_at.strftime('%B %d, %Y at %I:%M %p')}
Status: PAID ✅

========================================
ORDER ITEMS
========================================
{items_text}

========================================
PAYMENT SUMMARY
========================================
Subtotal:        KES {subtotal:.2f}
Delivery Fee:    KES {txn.order.delivery_fee:.2f}
----------------------------------------
TOTAL PAID:      KES {txn.order.total_amount:.2f}

Payment Method:  M-Pesa
Receipt Number:  {txn.mpesa_receipt_number}

========================================
DELIVERY INFORMATION
========================================
Delivery Address: {txn.order.get_delivery_location()}
Estimated Time:   30-60 minutes

========================================

Your order is being prepared and will be delivered shortly.

We'll send you a WhatsApp message when your order is out for delivery.

Need help? Contact us:
Phone/WhatsApp: 0115745813
Email: oyarodaniel740@gmail.com

Thank you for shopping with MyStore! ❤️

MyStore Team
"""
            
            send_mail(
                subject=f"✅ Order Confirmation #{txn.order.id} - MyStore",
                message=customer_email_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[customer_email],
                fail_silently=False,
            )

        # Customer confirmation with order summary
        items_count = order_items.count()
        
        send_whatsapp_message(
            f"Payment successful 🎉\n\n"
            f"Order #{txn.order.id}\n"
            f"Items: {items_count} product{'s' if items_count > 1 else ''}\n"
            f"Total: KES {txn.order.total_amount}\n"
            f"Receipt: {txn.mpesa_receipt_number}\n\n"
            f"Delivery to:\n{txn.order.get_delivery_location()}\n\n"
            f"ETA: 30-60 minutes\n\n"
            f"Thank you for shopping with MyStore! ❤️",
            txn.phone_number
        )

    else:
        txn.status = 'FAILED'
        send_whatsapp_message(
            f"Payment failed ❌\n"
            f"Order #{txn.order.id}\n"
            f"Reason: {txn.result_desc}",
            txn.phone_number
        )       

    txn.save()
    return HttpResponse(status=200)


def payment_status(request, order_id):
    txn = MpesaTransaction.objects.get(order_id=order_id)
    return JsonResponse({'status': txn.status})


def order_success(request):
    # Clear cart after successful order
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart.items.all().delete()
        except Cart.DoesNotExist:
            pass
    else:
        request.session.pop('cart', None)
        request.session.modified = True
    
    return render(request, 'store/order_success.html')


@login_required(login_url='/login/')
def profile_view(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=request.user.profile
        )
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
    
    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    
    return render(request, 'store/profile.html', context)


def verify_email(request, token):
    """Verify user's email address"""
    try:
        profile = Profile.objects.get(email_verification_token=token)
        
        # Check if token is expired (24 hours)
        if profile.email_verification_sent_at:
            expiry_time = profile.email_verification_sent_at + timedelta(hours=24)
            if timezone.now() > expiry_time:
                messages.error(request, 'Verification link has expired. Please request a new one.')
                return redirect('resend_verification')
        
        # Verify the email
        profile.email_verified = True
        profile.email_verification_token = None
        profile.save()
        
        messages.success(request, 'Email verified successfully! 🎉')
        return redirect('home')
        
    except Profile.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('home')


@login_required(login_url='/login/')
def resend_verification(request):
    """Resend email verification link"""
    if request.user.profile.email_verified:
        messages.info(request, 'Your email is already verified.')
        return redirect('profile')
    
    if request.method == 'POST':
        try:
            send_verification_email(request.user, request)
            messages.success(request, 'Verification email sent! Please check your inbox.')
        except Exception as e:
            messages.error(request, 'Failed to send verification email. Please try again later.')
        
        return redirect('profile')
    
    return render(request, 'store/resend_verification.html')


class CustomPasswordResetView(PasswordResetView):
    template_name = 'store/password_reset.html'
    email_template_name = 'store/password_reset_email.html'
    subject_template_name = 'store/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')
    form_class = CustomPasswordResetForm


def password_reset_done_view(request):
    return render(request, 'store/password_reset_done.html')


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'store/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')
    form_class = CustomSetPasswordForm


def password_reset_complete_view(request):
    return render(request, 'store/password_reset_complete.html')

# ADD THIS VIEW TO YOUR views.py FILE

@login_required(login_url='/login/')
def order_history(request):
    """
    Display user's order history with all details
    """
    # Get all orders for the current user, ordered by most recent first
    orders = Order.objects.filter(
        user=request.user
    ).select_related(
        'plot__main_area'
    ).prefetch_related(
        'items__product',
        'mpesa_transaction'
    ).order_by('-created_at')
    
    # Separate orders by status
    paid_orders = orders.filter(is_paid=True)
    pending_orders = orders.filter(is_paid=False)
    
    context = {
        'orders': orders,
        'paid_orders': paid_orders,
        'pending_orders': pending_orders,
        'total_orders': orders.count(),
        'total_spent': sum(order.total_amount for order in paid_orders),
    }
    
    return render(request, 'store/order_history.html', context)


@login_required(login_url='/login/')
def order_detail(request, order_id):
    """
    Display detailed view of a specific order
    """
    order = get_object_or_404(
        Order.objects.select_related(
            'plot__main_area'
        ).prefetch_related(
            'items__product',
            'mpesa_transaction'
        ),
        id=order_id,
        user=request.user  # Ensure user can only view their own orders
    )
    
    context = {
        'order': order,
    }
    
    return render(request, 'store/order_detail.html', context)