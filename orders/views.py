from datetime import timedelta
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cart, CartItem, Expense, Order, OrderItem
from .serializers import (
    CartItemCreateSerializer,
    CartItemSerializer,
    CartItemUpdateSerializer,
    CartSerializer,
    ExpenseSerializer,
    OrderCreateSerializer,
    OrderSerializer,
)


MONEY_OUTPUT = DecimalField(max_digits=18, decimal_places=2)
REVENUE_EXPR = ExpressionWrapper(F("price") * F("quantity"), output_field=MONEY_OUTPUT)
COST_EXPR = ExpressionWrapper(F("cost_price") * F("quantity"), output_field=MONEY_OUTPUT)


def _sum_or_zero(queryset, expression):
    value = queryset.aggregate(total=Sum(expression))["total"]
    return value or Decimal("0.00")


def _as_decimal(value):
    return value if isinstance(value, Decimal) else Decimal(value or 0)


def get_user_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


class DeliveryMapView(TemplateView):
    template_name = "orders/delivery_map.html"


class CartView(generics.RetrieveAPIView):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return get_user_cart(self.request.user)


class CartItemListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        cart = get_user_cart(self.request.user)
        return cart.items.select_related("product")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CartItemCreateSerializer
        return CartItemSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = get_user_cart(request.user)
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity},
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        output = CartSerializer(cart)
        return Response(
            output.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CartItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "item_id"

    def get_queryset(self):
        cart = get_user_cart(self.request.user)
        return cart.items.select_related("product")

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return CartItemUpdateSerializer
        return CartItemSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CartSerializer(instance.cart).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        cart = instance.cart
        instance.delete()
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class CartClearView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        cart = get_user_cart(request.user)
        cart.items.all().delete()
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().prefetch_related("items__product")
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ["expense_date"]
    search_fields = ["title", "note"]
    ordering_fields = ["expense_date", "created_at", "amount"]


class FinanceOverviewAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        chart_days = self._read_positive_int(
            request.query_params.get("chart_days"), default=30, max_value=365
        )
        top_limit = self._read_positive_int(
            request.query_params.get("top_limit"), default=10, max_value=100
        )

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

        product_profit = self._product_profit_rows(sales_items)
        top_products = product_profit[:top_limit]
        daily_revenue_chart = self._daily_revenue_chart(sales_items, days=chart_days)

        return Response(
            {
                "total_revenue": total_revenue,
                "total_expense": total_expense,
                "total_cost": total_cost,
                "gross_profit": gross_profit,
                "net_profit": net_profit,
                "average_check": average_check,
                "profit_percent": profit_percent,
                "total_orders": order_count,
                "revenue_periods": revenue_periods,
                "daily_revenue_chart": daily_revenue_chart,
                "top_products": top_products,
                "product_profit": product_profit,
            }
        )

    def _read_positive_int(self, value, default, max_value):
        try:
            parsed = int(value)
            if parsed < 1:
                return default
            return min(parsed, max_value)
        except (TypeError, ValueError):
            return default

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
            points.append(
                {
                    "date": day.isoformat(),
                    "label": day.strftime("%d-%m"),
                    "revenue": revenue,
                }
            )

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
