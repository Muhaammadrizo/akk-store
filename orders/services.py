import json
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
