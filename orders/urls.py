from rest_framework.routers import DefaultRouter

from .views import OrderViewSet

router = DefaultRouter()
router.include_format_suffixes = False
router.register("orders", OrderViewSet, basename="order")

urlpatterns = router.urls
