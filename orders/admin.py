from django.contrib import admin

from .models import Cart, CartItem, Order, OrderItem


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "status",
        "delivery_type",
        "payment_method",
        "total_price",
        "created_at",
    )
    list_filter = ("status", "delivery_type", "payment_method")
    search_fields = ("id", "user__username", "user__email", "delivery_address")
    date_hierarchy = "created_at"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity", "price")
    list_filter = ("product",)
    search_fields = ("order__id", "product__name")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "updated_at")
    search_fields = ("user__username", "user__email")


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "product", "quantity", "created_at")
    list_filter = ("product",)
    search_fields = ("cart__user__username", "product__name")
