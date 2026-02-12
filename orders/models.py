from decimal import Decimal

from django.conf import settings
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        CANCELED = "canceled", "Canceled"

    class DeliveryType(models.TextChoices):
        PICKUP = "pickup", "Pickup from store"
        COURIER = "courier", "Courier delivery"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="orders", on_delete=models.CASCADE
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    delivery_type = models.CharField(
        max_length=20, choices=DeliveryType.choices, default=DeliveryType.PICKUP
    )
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    delivery_address = models.CharField(max_length=255, blank=True)
    delivery_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    delivery_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def recalc_total(self):
        total = Decimal("0.00")
        for item in self.items.all():
            total += item.price * item.quantity
        self.total_price = total
        self.save(update_fields=["total_price"])

    def __str__(self):
        return f"Order #{self.pk} ({self.user})"


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name="cart", on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_price(self):
        total = Decimal("0.00")
        for item in self.items.select_related("product"):
            total += item.product.price * item.quantity
        return total

    def __str__(self):
        return f"Cart of {self.user}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(
        "catalog.Product", related_name="cart_items", on_delete=models.PROTECT
    )
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("cart", "product")

    @property
    def total_price(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.product} x {self.quantity}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(
        "catalog.Product", related_name="order_items", on_delete=models.PROTECT
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product} x {self.quantity}"
