from django.contrib import admin
from .models import (
    Category, Product, Order, OrderItem, MpesaTransaction, 
    Profile, Cart, CartItem, MainArea, Plot, PlotImage
)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock_quantity')
    list_filter = ('category',)
    search_fields = ('name',)
    list_editable = ('stock_quantity',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'get_location',
        'total_amount',
        'is_paid',
        'created_at'
    )
    list_filter = ('is_paid', 'created_at')
    search_fields = ('id', 'user__username')
    date_hierarchy = 'created_at'
    
    def get_location(self, obj):
        return obj.get_delivery_location()
    get_location.short_description = 'Delivery Location'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price')


@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'order',
        'phone_number',
        'status',
        'result_code',
        'mpesa_receipt_number',
        'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('mpesa_receipt_number', 'phone_number')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 
        'phone_number', 
        'get_location',
        'location_setup_complete',
        'updated_at'
    )
    search_fields = ('user__username', 'phone_number')
    list_filter = ('location_setup_complete', 'updated_at')
    
    def get_location(self, obj):
        return obj.get_delivery_location()
    get_location.short_description = 'Location'


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('added_at',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_total_items', 'created_at', 'updated_at')
    search_fields = ('user__username',)
    list_filter = ('created_at', 'updated_at')
    inlines = [CartItemInline]
    
    def get_total_items(self, obj):
        return obj.get_total_items()
    get_total_items.short_description = 'Total Items'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'get_subtotal', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('cart__user__username', 'product__name')
    
    def get_subtotal(self, obj):
        return f"KSH {obj.get_subtotal()}"
    get_subtotal.short_description = 'Subtotal'


# NEW: Main Area Admin
@admin.register(MainArea)
class MainAreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'delivery_fee', 'is_active', 'plot_count', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    prepopulated_fields = {}
    
    def plot_count(self, obj):
        return obj.plots.count()
    plot_count.short_description = 'Number of Plots'


# NEW: Plot Image Inline
class PlotImageInline(admin.TabularInline):
    model = PlotImage
    extra = 1
    fields = ('image', 'caption', 'is_primary', 'order')
    readonly_fields = ('uploaded_at',)


# NEW: Plot Admin
@admin.register(Plot)
class PlotAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'main_area', 
        'is_active', 
        'image_count',
        'resident_count',
        'created_at'
    )
    list_filter = ('main_area', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'landmark_description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [PlotImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'main_area', 'is_active')
        }),
        ('Location Details', {
            'fields': ('description', 'landmark_description')
        }),
    )
    
    def image_count(self, obj):
        return obj.images.count()
    image_count.short_description = 'Images'
    
    def resident_count(self, obj):
        return obj.residents.count()
    resident_count.short_description = 'Residents'


# NEW: Plot Image Admin
@admin.register(PlotImage)
class PlotImageAdmin(admin.ModelAdmin):
    list_display = (
        'plot', 
        'image_thumbnail',
        'caption', 
        'is_primary', 
        'order',
        'uploaded_at'
    )
    list_filter = ('is_primary', 'plot__main_area', 'uploaded_at')
    search_fields = ('plot__name', 'caption')
    list_editable = ('is_primary', 'order')
    
    def image_thumbnail(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" width="50" height="50" style="object-fit: cover;" />'
        return '-'
    image_thumbnail.short_description = 'Preview'
    image_thumbnail.allow_tags = True


admin.site.register(Category)