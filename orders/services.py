import json
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import Request, urlopen


NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"


def reverse_geocode_address(latitude, longitude):
    params = urlencode(
        {
            "format": "jsonv2",
            "lat": latitude,
            "lon": longitude,
            "zoom": 18,
            "addressdetails": 1,
        }
    )
    request = Request(
        f"{NOMINATIM_REVERSE_URL}?{params}",
        headers={"User-Agent": "akk-order-service/1.0"},
    )
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("display_name", "").strip()
    except Exception:
        return ""


def assign_courier_to_order(order):
    """
    Buyurtma uchun mos kurer tanlash.
    Kurer mashinasining sig'imi buyurtma hajmiga mos kelishi kerak.
    """
    from users.models import Courier
    
    # Faqat courier delivery uchun kurer tanlash
    if order.delivery_type != Order.DeliveryType.COURIER:
        return None
    
    # Buyurtma hajmini hisoblash
    order_volume = Decimal("0.00")
    for item in order.items.select_related('product'):
        # Har bir mahsulotning hajmini miqdoriga ko'paytirish
        product_volume = item.product.volume or Decimal("0.00")
        order_volume += product_volume * Decimal(str(item.quantity))
    
    # Agar hajm 0 bo'lsa, minimal hajm sifatida 0.01 kub metr deb olamiz
    if order_volume == 0:
        order_volume = Decimal("0.01")
    
    # Faol kurerlarni topish va sig'imiga qarab saralash
    available_couriers = Courier.objects.filter(
        is_active=True,
        car_capacity__gte=order_volume
    ).order_by('car_capacity')  # Eng kichik mos keladigan mashinani tanlash
    
    if available_couriers.exists():
        # Eng kichik mos keladigan kurer tanlash
        courier = available_couriers.first()
        order.courier = courier
        order.save(update_fields=['courier'])
        return courier
    
    # Agar mos kurer topilmasa, None qaytariladi
    return None
