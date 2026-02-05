from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from catalog.models import Product
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "quantity", "price"]
        read_only_fields = ["price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "status", "total_price", "created_at", "updated_at", "items"]


class OrderCreateItemSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True)
    )
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderCreateItemSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = ["id", "items", "status", "total_price", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "total_price", "created_at", "updated_at"]

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        user = self.context["request"].user
        with transaction.atomic():
            order = Order.objects.create(user=user)
            total = Decimal("0.00")
            for item in items_data:
                product = item["product"]
                quantity = item["quantity"]
                price = product.price
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=price,
                )
                total += price * quantity
            order.total_price = total
            order.save(update_fields=["total_price"])
        return order
