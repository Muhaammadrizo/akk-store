from django.contrib import admin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", 'slug',)
    list_filter = ("name",)
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "price",
        "cost_price",
        "old_price",
        "profit_per_unit_display",
        "total_stock_in",
        "total_stock_out",
        "stock",
        "is_active",
        "category",
    )
    list_filter = ("is_active", "category")
    search_fields = ("name",)
    readonly_fields = ("total_stock_in", "total_stock_out", "profit_per_unit_display")
    fields = (
        "name",
        "category",
        "description",
        "price",
        "old_price",
        "cost_price",
        "profit_per_unit_display",
        "stock",
        "total_stock_in",
        "total_stock_out",
        "is_active",
        "image",
    )

    @admin.display(description="1 dona foyda")
    def profit_per_unit_display(self, obj):
        return obj.profit_per_unit
