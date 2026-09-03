def cart_count(request):
    """
    Context processor to provide cart count for both authenticated and anonymous users
    """
    if request.user.is_authenticated:
        try:
            from .models import Cart
            cart = Cart.objects.get(user=request.user)
            count = cart.get_total_items()
        except:
            count = 0
    else:
        cart = request.session.get('cart', {})
        count = sum(item['quantity'] for item in cart.values())
    
    return {
        'cart_count': count
    }