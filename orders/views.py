from django.views.generic import TemplateView
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response

from .models import Cart, CartItem, Order
from .serializers import (
    CartItemCreateSerializer,
    CartItemSerializer,
    CartItemUpdateSerializer,
    CartSerializer,
    OrderCreateSerializer,
    OrderSerializer,
)


def get_user_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


class DeliveryMapView(TemplateView):
    template_name = "orders/delivery_map.html"


class CartView(generics.RetrieveAPIView):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return get_user_cart(self.request.user)


class CartItemListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        cart = get_user_cart(self.request.user)
        return cart.items.select_related("product")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CartItemCreateSerializer
        return CartItemSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = get_user_cart(request.user)
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity},
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        output = CartSerializer(cart)
        return Response(
            output.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CartItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "item_id"

    def get_queryset(self):
        cart = get_user_cart(self.request.user)
        return cart.items.select_related("product")

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return CartItemUpdateSerializer
        return CartItemSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CartSerializer(instance.cart).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        cart = instance.cart
        instance.delete()
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class CartClearView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        cart = get_user_cart(request.user)
        cart.items.all().delete()
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().prefetch_related("items__product")
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer
