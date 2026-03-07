from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Courier

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]


class UserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6, required=False)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "email": {"required": False, "allow_blank": True},
            "first_name": {"required": False, "allow_blank": True},
            "last_name": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Bu maydon majburiy."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["username", "email", "password", "first_name", "last_name"]
        extra_kwargs = {
            "email": {"required": False, "allow_blank": True},
            "first_name": {"required": False, "allow_blank": True},
            "last_name": {"required": False, "allow_blank": True},
        }

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class CourierSerializer(serializers.ModelSerializer):
    """Kurer ma'lumotlarini ko'rsatish uchun"""
    full_name = serializers.ReadOnlyField()
    user = UserSerializer(read_only=True)

    class Meta:
        model = Courier
        fields = [
            'id', 'user', 'phone', 'first_name', 'last_name', 
            'full_name', 'avatar', 'car_number', 'car_name', 
            'car_capacity', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CourierCreateSerializer(serializers.ModelSerializer):
    """Kurer yaratish uchun - faqat admin"""
    username = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=6)

    class Meta:
        model = Courier
        fields = [
            'username', 'password', 'phone', 'first_name', 'last_name',
            'avatar', 'car_number', 'car_name', 'car_capacity'
        ]

    def validate_phone(self, value):
        if Courier.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Bu telefon raqami allaqachon mavjud.")
        return value

    def validate_car_number(self, value):
        if Courier.objects.filter(car_number=value).exists():
            raise serializers.ValidationError("Bu mashina raqami allaqachon mavjud.")
        return value

    def create(self, validated_data):
        username = validated_data.pop('username')
        password = validated_data.pop('password')
        
        # User yaratish
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        
        # Courier yaratish
        courier = Courier.objects.create(user=user, **validated_data)
        return courier


class CourierUpdateSerializer(serializers.ModelSerializer):
    """Kurer ma'lumotlarini yangilash uchun"""
    
    class Meta:
        model = Courier
        fields = [
            'phone', 'first_name', 'last_name', 'avatar',
            'car_number', 'car_name', 'car_capacity', 'is_active'
        ]

    def validate_phone(self, value):
        if self.instance and Courier.objects.filter(phone=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Bu telefon raqami allaqachon mavjud.")
        return value

    def validate_car_number(self, value):
        if self.instance and Courier.objects.filter(car_number=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Bu mashina raqami allaqachon mavjud.")
        return value
