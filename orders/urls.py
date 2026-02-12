from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CartClearView,
    CartItemDetailView,
    CartItemListCreateView,
    CartView,
    DeliveryMapView,
    OrderViewSet,
)

router = DefaultRouter()
router.include_format_suffixes = False
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart-detail"),
    path("cart/items/", CartItemListCreateView.as_view(), name="cart-items"),
    path("cart/items/<int:item_id>/", CartItemDetailView.as_view(), name="cart-item-detail"),
    path("cart/clear/", CartClearView.as_view(), name="cart-clear"),
    path("orders/delivery-map/", DeliveryMapView.as_view(), name="delivery-map"),
]
urlpatterns += router.urls
