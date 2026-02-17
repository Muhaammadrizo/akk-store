from decimal import Decimal

from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=120, unique=True)



    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    old_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    stock = models.PositiveIntegerField()
    total_stock_in = models.PositiveIntegerField(default=0)
    total_stock_out = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    category = models.ForeignKey(Category, related_name="products", on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/', null=True, blank=True)

    @property
    def profit_per_unit(self):
        return self.price - self.cost_price

    @property
    def total_profit(self):
        return Decimal(self.total_stock_out) * self.profit_per_unit

    def save(self, *args, **kwargs):
        previous_stock = None
        stock_increased = False
        if self.pk:
            previous_stock = (
                Product.objects.filter(pk=self.pk).values_list("stock", flat=True).first()
            )

        if previous_stock is None:
            if self.total_stock_in == 0:
                self.total_stock_in = self.stock
                stock_increased = True
        elif self.stock > previous_stock:
            self.total_stock_in += self.stock - previous_stock
            stock_increased = True

        if stock_increased and kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"total_stock_in"}

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
