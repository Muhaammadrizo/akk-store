from rest_framework.routers import DefaultRouter

from .views import UserViewSet, CourierViewSet

router = DefaultRouter()
router.include_format_suffixes = False
router.register("users", UserViewSet, basename="user")
router.register("couriers", CourierViewSet, basename="courier")

urlpatterns = router.urls
