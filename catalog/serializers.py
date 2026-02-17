from rest_framework import serializers

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    profit_per_unit = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "price",
            "old_price",
            "cost_price",
            "profit_per_unit",
            "description",
            "stock",
            "total_stock_in",
            "total_stock_out",
            "is_active",
            "category",
            "category_name",
            "image",
        ]
        read_only_fields = ["total_stock_in", "total_stock_out", "profit_per_unit"]

    def get_profit_per_unit(self, obj):
        return obj.profit_per_unit
