from rest_framework import generics, permissions, viewsets, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action

from .models import User, Courier
from .serializers import (
    RegisterSerializer, 
    UserSerializer, 
    UserWriteSerializer,
    CourierSerializer,
    CourierCreateSerializer,
    CourierUpdateSerializer
)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        data = {
            "user": UserSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
        return Response(data, status=201)


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-id")
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return queryset
        if user.is_authenticated:
            return queryset.filter(pk=user.pk)
        return queryset.none()

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return UserWriteSerializer
        return UserSerializer

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.user.is_staff:
            return
        if obj != request.user:
            self.permission_denied(
                request, message="Siz faqat o'zingizning profilingizni ko'ra olasiz."
            )


class CourierViewSet(viewsets.ModelViewSet):
    """Kurerlar uchun ViewSet - faqat admin qo'sha oladi"""
    queryset = Courier.objects.all().select_related('user')
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'create':
            return CourierCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CourierUpdateSerializer
        return CourierSerializer

    def get_permissions(self):
        if self.action == 'create':
            # Faqat admin qo'sha oladi
            return [permissions.IsAdminUser()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Faqat admin o'zgartira oladi
            return [permissions.IsAdminUser()]
        # Barcha autentifikatsiya qilingan foydalanuvchilar ko'ra oladi
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Agar kurer bo'lsa, faqat o'z ma'lumotlarini ko'radi
        if hasattr(user, 'courier_profile'):
            return queryset.filter(user=user)
        
        # Agar admin bo'lsa, barcha kurerlarni ko'radi
        if user.is_staff:
            return queryset
        
        # Boshqa foydalanuvchilar ko'ra olmaydi
        return queryset.none()

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Kurer o'z ma'lumotlarini ko'radi"""
        try:
            courier = request.user.courier_profile
            serializer = self.get_serializer(courier)
            return Response(serializer.data)
        except Courier.DoesNotExist:
            return Response(
                {'detail': 'Siz kurer emassiz.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def orders(self, request, pk=None):
        """Kurerning buyurtmalarini ko'rsatish"""
        courier = self.get_object()
        from orders.models import Order
        from orders.serializers import OrderSerializer
        
        orders = Order.objects.filter(courier=courier).prefetch_related('items__product')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
