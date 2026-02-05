from rest_framework import permissions, viewsets

from .filters import ProductFilter
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True).select_related("category")
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = ProductFilter
    search_fields = ["name"]
