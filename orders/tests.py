from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Category, Product
from orders.models import Expense, Order, OrderItem

User = get_user_model()


class OrderFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.force_authenticate(user=self.user)

        self.category = Category.objects.create(name="Tools", slug="tools")
        self.product = Product.objects.create(
            name="Hammer",
            price="100000.00",
            old_price="120000.00",
            cost_price="70000.00",
            description="Steel hammer",
            stock=50,
            is_active=True,
            category=self.category,
        )

    def test_create_order_from_cart(self):
        add_to_cart_url = reverse("cart-items")
        response = self.client.post(
            add_to_cart_url, {"product": self.product.id, "quantity": 2}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        create_order_url = reverse("order-list")
        response = self.client.post(
            create_order_url,
            {"delivery_type": "pickup", "payment_method": "cash"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        order = Order.objects.get(pk=response.data["id"])
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(str(order.total_price), "200000.00")
        self.assertEqual(order.delivery_type, "pickup")
        self.assertEqual(order.payment_method, "cash")
        self.assertEqual(self.user.cart.items.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 48)
        self.assertEqual(self.product.total_stock_out, 2)
        self.assertEqual(str(order.items.first().cost_price), "70000.00")

    def test_courier_requires_coordinates(self):
        create_order_url = reverse("order-list")
        response = self.client.post(
            create_order_url,
            {
                "delivery_type": "courier",
                "payment_method": "card",
                "items": [{"product": self.product.id, "quantity": 1}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("delivery_location", response.data)

    @patch("orders.serializers.reverse_geocode_address", return_value="Tashkent, Yunusobod")
    def test_courier_order_saves_address(self, _mock_reverse):
        create_order_url = reverse("order-list")
        response = self.client.post(
            create_order_url,
            {
                "delivery_type": "courier",
                "payment_method": "card",
                "delivery_latitude": "41.311081",
                "delivery_longitude": "69.240562",
                "items": [{"product": self.product.id, "quantity": 1}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get(pk=response.data["id"])
        self.assertEqual(order.delivery_address, "Tashkent, Yunusobod")
        self.assertEqual(str(order.delivery_latitude), "41.311081")
        self.assertEqual(str(order.delivery_longitude), "69.240562")

    def test_create_order_rejects_if_stock_is_not_enough(self):
        create_order_url = reverse("order-list")
        response = self.client.post(
            create_order_url,
            {
                "delivery_type": "pickup",
                "payment_method": "cash",
                "items": [{"product": self.product.id, "quantity": 100}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.data)


class FinanceApiTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_superuser(
            username="admin",
            password="adminpass123",
            email="admin@example.com",
        )
        self.user = User.objects.create_user(username="user1", password="userpass123")

        self.category = Category.objects.create(name="Electronics", slug="electronics")
        self.product1 = Product.objects.create(
            name="Drill",
            price="200.00",
            cost_price="130.00",
            stock=100,
            is_active=True,
            category=self.category,
        )
        self.product2 = Product.objects.create(
            name="Saw",
            price="100.00",
            cost_price="60.00",
            stock=100,
            is_active=True,
            category=self.category,
        )

        self.order = Order.objects.create(
            user=self.user,
            status=Order.Status.PAID,
            delivery_type=Order.DeliveryType.PICKUP,
            payment_method=Order.PaymentMethod.CASH,
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            quantity=1,
            price="200.00",
            cost_price="130.00",
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product2,
            quantity=2,
            price="100.00",
            cost_price="60.00",
        )
        self.order.recalc_total()

        canceled = Order.objects.create(
            user=self.user,
            status=Order.Status.CANCELED,
            delivery_type=Order.DeliveryType.PICKUP,
            payment_method=Order.PaymentMethod.CASH,
        )
        OrderItem.objects.create(
            order=canceled,
            product=self.product1,
            quantity=10,
            price="200.00",
            cost_price="130.00",
        )

        Expense.objects.create(
            title="Rent",
            amount="50.00",
            expense_date=timezone.localdate(),
            note="monthly",
        )

    def test_staff_can_get_finance_overview(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(reverse("finance-overview"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["total_revenue"]), Decimal("400.00"))
        self.assertEqual(Decimal(response.data["total_cost"]), Decimal("250.00"))
        self.assertEqual(Decimal(response.data["gross_profit"]), Decimal("150.00"))
        self.assertEqual(Decimal(response.data["total_expense"]), Decimal("50.00"))
        self.assertEqual(Decimal(response.data["net_profit"]), Decimal("100.00"))
        self.assertEqual(Decimal(response.data["average_check"]), Decimal("400.00"))
        self.assertEqual(response.data["total_orders"], 1)
        self.assertEqual(len(response.data["revenue_periods"]), 5)
        self.assertEqual(response.data["top_products"][0]["name"], "Drill")

    def test_non_staff_cannot_get_finance_overview(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("finance-overview"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_crud_expense_api(self):
        self.client.force_authenticate(user=self.staff)

        create_response = self.client.post(
            reverse("expense-list"),
            {
                "title": "Logistics",
                "amount": "25.00",
                "expense_date": timezone.localdate().isoformat(),
                "note": "delivery",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        expense_id = create_response.data["id"]
        list_response = self.client.get(reverse("expense-list"))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(list_response.data), 2)

        update_response = self.client.patch(
            reverse("expense-detail", args=[expense_id]),
            {"amount": "30.00"},
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(update_response.data["amount"]), Decimal("30.00"))

    def test_non_staff_cannot_create_expense(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("expense-list"),
            {
                "title": "Transport",
                "amount": "12.00",
                "expense_date": timezone.localdate().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
