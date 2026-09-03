from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from cloudinary.models import CloudinaryField  # ← ADDED


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products'
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    product_img = CloudinaryField(          # ← CHANGED from ImageField
        'image',
        default='fallback',
        blank=True,
        transformation=[{'quality': 'auto', 'fetch_format': 'auto'}]
    )

    def stock_status(self):
        if self.stock_quantity == 0:
            return 'out'
        elif self.stock_quantity <= 5:
            return 'low'
        return 'in'

    def __str__(self):
        return self.name


class MainArea(models.Model):
    """Represents main delivery areas like Maganda, TTC, Vision, Nanga"""
    name = models.CharField(max_length=100, unique=True)
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField(blank=True, help_text="Brief description of the area")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} @ Ksh {self.delivery_fee}"


class Plot(models.Model):
    """Represents individual plots within main areas"""
    main_area = models.ForeignKey(
        MainArea,
        on_delete=models.CASCADE,
        related_name='plots'
    )
    name = models.CharField(max_length=200, help_text="e.g., Kwa Sammy, Kwa Mwalimu Masilio")
    slug = models.SlugField(unique=True)
    description = models.TextField(
        blank=True,
        help_text="Location description with landmarks"
    )
    landmark_description = models.TextField(
        blank=True,
        help_text="Describe location relative to nearby landmarks"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['main_area', 'name']
        unique_together = ('main_area', 'name')

    def __str__(self):
        return f"{self.name} ({self.main_area.name})"

    def get_primary_image(self):
        """Get the primary image or fall back to first"""
        return self.images.filter(is_primary=True).first() or self.images.first()


class PlotImage(models.Model):
    """Multiple images for each plot"""
    plot = models.ForeignKey(Plot, on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField(                # ← CHANGED from ImageField
        'image',
        folder='plots',
        transformation=[{'quality': 'auto', 'fetch_format': 'auto'}]
    )
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(
        default=False,
        help_text="Main image shown in selection view"
    )
    order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'order', 'uploaded_at']

    def __str__(self):
        return f"{self.plot.name} - Image {self.id}"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per plot
        if self.is_primary:
            PlotImage.objects.filter(
                plot=self.plot,
                is_primary=True
            ).update(is_primary=False)
        super().save(*args, **kwargs)


class Order(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        null=True,
        blank=True
    )
    plot = models.ForeignKey(
        Plot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Specific plot for delivery"
    )
    location = models.CharField(max_length=50, blank=True)
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Order #{self.id}"

    def get_delivery_location(self):
        if self.plot:
            return f"{self.plot.name}, {self.plot.main_area.name}"
        return self.location


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return self.product.name


class MpesaTransaction(models.Model):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='mpesa_transaction'
    )
    phone_number = models.CharField(max_length=20)
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
    merchant_request_id = models.CharField(max_length=100, blank=True, null=True)
    result_code = models.IntegerField(blank=True, null=True)
    result_desc = models.CharField(max_length=255, blank=True, null=True)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('SUCCESS', 'Success'),
            ('FAILED', 'Failed'),
        ],
        default='PENDING'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"M-Pesa Order {self.order.id} - {self.status}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = CloudinaryField(      # ← CHANGED from ImageField
        'image',
        folder='profile_pics',
        blank=True,
        null=True,
        default=None,
        transformation=[{'quality': 'auto', 'fetch_format': 'auto'}]
    )
    bio = models.TextField(max_length=500, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    default_plot = models.ForeignKey(
        Plot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='residents',
        help_text="Default delivery location"
    )
    location = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    location_setup_complete = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def has_profile_picture(self):
        return bool(self.profile_picture)

    def get_delivery_location(self):
        if self.default_plot:
            return f"{self.default_plot.name}, {self.default_plot.main_area.name}"
        return self.location or "Not set"

    def get_profile_picture_url(self):
        if self.profile_picture:
            import cloudinary.utils
            return cloudinary.utils.cloudinary_url(
                str(self.profile_picture), format='jpg', secure=True
            )[0]
        return None


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())

    def get_total_price(self):
        return sum(item.get_subtotal() for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    def get_subtotal(self):
        return self.product.price * self.quantity


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

@receiver(post_save, sender=User)
def create_user_cart(sender, instance, created, **kwargs):
    if created:
        Cart.objects.create(user=instance)