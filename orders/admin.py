from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import Cart, CartItem, Expense, Order, OrderItem


MONEY_OUTPUT = DecimalField(max_digits=18, decimal_places=2)
REVENUE_EXPR = ExpressionWrapper(F("price") * F("quantity"), output_field=MONEY_OUTPUT)
COST_EXPR = ExpressionWrapper(F("cost_price") * F("quantity"), output_field=MONEY_OUTPUT)


def _sum_or_zero(queryset, expression):
    value = queryset.aggregate(total=Sum(expression))["total"]
    return value or Decimal("0.00")


def _as_decimal(value):
    return value if isinstance(value, Decimal) else Decimal(value or 0)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "status",
        "delivery_type",
        "payment_method",
        "total_price",
        "created_at",
    )
    list_filter = ("status", "delivery_type", "payment_method")
    search_fields = ("id", "user__username", "user__email", "delivery_address")
    date_hierarchy = "created_at"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity", "price", "cost_price", "profit")
    list_filter = ("product",)
    search_fields = ("order__id", "product__name")

    @admin.display(description="Foyda")
    def profit(self, obj):
        return obj.line_profit


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "updated_at")
    search_fields = ("user__username", "user__email")


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "product", "quantity", "created_at")
    list_filter = ("product",)
    search_fields = ("cart__user__username", "product__name")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    change_list_template = "admin/orders/expense/change_list.html"
    list_display = ("id", "title", "amount", "expense_date", "created_at")
    list_filter = ("expense_date",)
    search_fields = ("title", "note")
    date_hierarchy = "expense_date"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(self._finance_context())
        return super().changelist_view(request, extra_context=extra_context)

    def _finance_context(self):
        sales_orders = Order.objects.exclude(status=Order.Status.CANCELED)
        sales_items = OrderItem.objects.exclude(
            order__status=Order.Status.CANCELED
        ).select_related("product")

        total_revenue = _sum_or_zero(sales_items, REVENUE_EXPR)
        total_cost = _sum_or_zero(sales_items, COST_EXPR)
        gross_profit = total_revenue - total_cost
        total_expense = _as_decimal(Expense.objects.aggregate(total=Sum("amount"))["total"])
        net_profit = gross_profit - total_expense

        order_count = sales_orders.count()
        average_check = total_revenue / order_count if order_count else Decimal("0.00")
        profit_percent = (
            (net_profit / total_revenue) * Decimal("100")
            if total_revenue > 0
            else Decimal("0.00")
        )

        revenue_periods = [
            {"label": "1 kun", "value": self._revenue_for_days(sales_items, 1)},
            {"label": "7 kun", "value": self._revenue_for_days(sales_items, 7)},
            {"label": "30 kun", "value": self._revenue_for_days(sales_items, 30)},
            {"label": "90 kun", "value": self._revenue_for_days(sales_items, 90)},
            {"label": "Barchasi", "value": total_revenue},
        ]

        product_profit_rows = self._product_profit_rows(sales_items)
        top_products = product_profit_rows[:10]
        daily_revenue_chart = self._daily_revenue_chart(sales_items, days=30)

        return {
            "finance_total_revenue": total_revenue,
            "finance_total_expense": total_expense,
            "finance_total_cost": total_cost,
            "finance_gross_profit": gross_profit,
            "finance_net_profit": net_profit,
            "finance_average_check": average_check,
            "finance_profit_percent": profit_percent,
            "finance_revenue_periods": revenue_periods,
            "finance_daily_revenue_chart": daily_revenue_chart,
            "finance_product_profit_rows": product_profit_rows,
            "finance_top_products": top_products,
        }

    def _revenue_for_days(self, sales_items, days):
        since = timezone.now() - timedelta(days=days)
        return _sum_or_zero(sales_items.filter(order__created_at__gte=since), REVENUE_EXPR)

    def _daily_revenue_chart(self, sales_items, days=30):
        start_day = timezone.localdate() - timedelta(days=days - 1)

        daily_rows = (
            sales_items.filter(order__created_at__date__gte=start_day)
            .annotate(day=TruncDate("order__created_at"))
            .values("day")
            .annotate(revenue=Sum(REVENUE_EXPR))
            .order_by("day")
        )
        daily_map = {row["day"]: _as_decimal(row["revenue"]) for row in daily_rows}

        points = []
        for offset in range(days):
            day = start_day + timedelta(days=offset)
            revenue = daily_map.get(day, Decimal("0.00"))
            points.append({"label": day.strftime("%d-%m"), "revenue": revenue})

        max_revenue = max((point["revenue"] for point in points), default=Decimal("0.00"))
        for point in points:
            if max_revenue > 0:
                point["percent"] = float((point["revenue"] / max_revenue) * Decimal("100"))
            else:
                point["percent"] = 0.0

        return points

    def _product_profit_rows(self, sales_items):
        rows = (
            sales_items.values("product_id", "product__name")
            .annotate(
                quantity_sold=Sum("quantity"),
                revenue=Sum(REVENUE_EXPR),
                cost=Sum(COST_EXPR),
            )
            .order_by("-revenue")
        )

        product_rows = []
        for row in rows:
            revenue = _as_decimal(row["revenue"])
            cost = _as_decimal(row["cost"])
            profit = revenue - cost
            margin_percent = (
                (profit / revenue) * Decimal("100") if revenue > 0 else Decimal("0.00")
            )
            product_rows.append(
                {
                    "product_id": row["product_id"],
                    "name": row["product__name"],
                    "quantity_sold": row["quantity_sold"] or 0,
                    "revenue": revenue,
                    "cost": cost,
                    "profit": profit,
                    "margin_percent": margin_percent,
                }
            )
        return product_rows
