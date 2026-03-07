from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    pass


class Courier(models.Model):
    """Kurer modeli - faqat admin qo'sha oladi"""
    user = models.OneToOneField(
        User, 
        related_name="courier_profile", 
        on_delete=models.CASCADE,
        verbose_name="Foydalanuvchi"
    )
    phone = models.CharField(max_length=20, unique=True, verbose_name="Telefon raqami")
    first_name = models.CharField(max_length=100, verbose_name="Ism")
    last_name = models.CharField(max_length=100, verbose_name="Familya")
    avatar = models.ImageField(
        upload_to='couriers/avatars/', 
        null=True, 
        blank=True,
        verbose_name="Avatar rasm"
    )
    car_number = models.CharField(max_length=20, unique=True, verbose_name="Mashina raqami")
    car_name = models.CharField(max_length=100, verbose_name="Mashina nomi")
    car_capacity = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Mashina sig'imi (kub metr)",
        help_text="Mashina necha kub metr yuk tashiydi (masalan: 10.00)"
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqt")

    class Meta:
        verbose_name = "Kurer"
        verbose_name_plural = "Kurerlar"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.car_number}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"