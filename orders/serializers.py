from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from catalog.models import Product
from .models import Cart, CartItem, Order, OrderItem
from .services import reverse_geocode_address


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    price = serializers.DecimalField(
        source="product.price", max_digits=12, decimal_places=2, read_only=True
    )
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "product_name",
            "price",
            "quantity",
            "line_total",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "product_name",
            "price",
            "line_total",
            "created_at",
            "updated_at",
        ]

    def get_line_total(self, obj):
        return obj.total_price


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "user", "created_at", "updated_at", "items", "total_price"]
        read_only_fields = fields

    def get_total_price(self, obj):
        return obj.total_price


class CartItemCreateSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True)
    )
    quantity = serializers.IntegerField(min_value=1, default=1)


class CartItemUpdateSerializer(serializers.ModelSerializer):
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = CartItem
        fields = ["quantity"]


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
        fields = [
            "id",
            "status",
            "delivery_type",
            "payment_method",
            "delivery_address",
            "delivery_latitude",
            "delivery_longitude",
            "total_price",
            "created_at",
            "updated_at",
            "items",
        ]


class OrderCreateItemSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True)
    )
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderCreateItemSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Order
        fields = [
            "id",
            "items",
            "status",
            "delivery_type",
            "payment_method",
            "delivery_address",
            "delivery_latitude",
            "delivery_longitude",
            "total_price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "delivery_address",
            "total_price",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        delivery_type = attrs.get("delivery_type", Order.DeliveryType.PICKUP)
        latitude = attrs.get("delivery_latitude")
        longitude = attrs.get("delivery_longitude")

        if delivery_type == Order.DeliveryType.COURIER:
            if latitude is None or longitude is None:
                raise serializers.ValidationError(
                    {
                        "delivery_location": (
                            "Courier delivery uchun delivery_latitude va "
                            "delivery_longitude majburiy."
                        )
                    }
                )
        else:
            attrs["delivery_latitude"] = None
            attrs["delivery_longitude"] = None
        return attrs

    def _resolve_items(self, user, items_data):
        if items_data:
            return [(item["product"], item["quantity"]) for item in items_data], None

        cart = getattr(user, "cart", None)
        if not cart:
            raise serializers.ValidationError(
                {"items": "Order yaratish uchun items yuboring yoki cartga mahsulot qo'shing."}
            )

        cart_items = list(cart.items.select_related("product"))
        if not cart_items:
            raise serializers.ValidationError(
                {"items": "Order yaratish uchun items yuboring yoki cartga mahsulot qo'shing."}
            )

        return [(item.product, item.quantity) for item in cart_items], cart

    def create(self, validated_data):
        items_data = validated_data.pop("items", None)
        user = self.context["request"].user
        items_for_order, source_cart = self._resolve_items(user, items_data)

        delivery_type = validated_data.get("delivery_type", Order.DeliveryType.PICKUP)
        if delivery_type == Order.DeliveryType.COURIER:
            latitude = validated_data.get("delivery_latitude")
            longitude = validated_data.get("delivery_longitude")
            address = reverse_geocode_address(latitude, longitude)
            validated_data["delivery_address"] = (
                address or f"Lat {latitude}, Lon {longitude}"
            )
        else:
            validated_data["delivery_address"] = ""

        with transaction.atomic():
            order = Order.objects.create(user=user, **validated_data)
            total = Decimal("0.00")
            for product, quantity in items_for_order:
                price = product.price
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=price,
                )
                total += price * quantity
            order.total_price = total
            order.save(update_fields=["total_price", "delivery_address"])
            if source_cart is not None:
                source_cart.items.all().delete()
        return order
