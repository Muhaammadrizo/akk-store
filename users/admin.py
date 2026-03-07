from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from .models import User, Courier


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    pass


@admin.register(Courier)
class CourierAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'car_number', 'car_name', 'car_capacity', 'is_active', 'avatar_preview']
    list_filter = ['is_active', 'created_at']
    search_fields = ['first_name', 'last_name', 'phone', 'car_number', 'car_name']
    readonly_fields = ['created_at', 'updated_at', 'avatar_preview']
    autocomplete_fields = ['user']
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('user', 'phone', 'first_name', 'last_name', 'avatar', 'avatar_preview')
        }),
        ('Mashina ma\'lumotlari', {
            'fields': ('car_number', 'car_name', 'car_capacity')
        }),
        ('Holat', {
            'fields': ('is_active',)
        }),
        ('Vaqt', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover; border-radius: 50%;" />', obj.avatar.url)
        return "Rasm yo'q"
    avatar_preview.short_description = "Avatar"

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = "To'liq ism"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')

    def has_add_permission(self, request):
        # Faqat admin qo'sha oladi
        return request.user.is_superuser or request.user.is_staff

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_staff
