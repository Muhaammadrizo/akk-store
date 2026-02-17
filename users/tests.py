from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class UserApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="user1",
            password="testpass123",
            email="user1@example.com",
        )
        self.other_user = User.objects.create_user(
            username="user2",
            password="testpass123",
            email="user2@example.com",
        )
        self.staff = User.objects.create_superuser(
            username="admin",
            password="adminpass123",
            email="admin@example.com",
        )

    def test_anyone_can_create_user_from_users_endpoint(self):
        response = self.client.post(
            reverse("user-list"),
            {
                "username": "newuser",
                "password": "newpass123",
                "email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newuser").exists())
        created = User.objects.get(username="newuser")
        self.assertNotEqual(created.password, "newpass123")
        self.assertTrue(created.check_password("newpass123"))

    def test_authenticated_user_list_returns_only_self(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("user-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.user.id)

    def test_staff_user_list_returns_all(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get(reverse("user-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 3)

    def test_user_cannot_retrieve_other_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("user-detail", args=[self.other_user.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_update_own_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            reverse("user-detail", args=[self.user.id]),
            {"first_name": "Updated"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
