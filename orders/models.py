from decimal import Decimal

from django.conf import settings
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        CANCELED = "canceled", "Canceled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="orders", on_delete=models.CASCADE
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
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
