from rest_framework.routers import DefaultRouter

from .views import UserViewSet

router = DefaultRouter()
router.include_format_suffixes = False
router.register("users", UserViewSet, basename="user")

urlpatterns = router.urls
