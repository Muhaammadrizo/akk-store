from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Category, Product
from orders.models import Order

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
