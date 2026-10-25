import requests
from models import LocationResponse

PINCODE_API_URL = "https://api.postalpincode.in/pincode/{pincode}"


def fetch_pincode_from_api(pincode: str) -> dict | None:
    """Fetch pincode data from India Post API."""
    try:
        response = requests.get(PINCODE_API_URL.format(pincode=pincode), timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("Status") == "Success" and data.get("PostOffice"):
                return data["PostOffice"][0]
    except requests.RequestException:
        pass
    return None


def map_api_to_location_response(pincode: str, api_data: dict) -> LocationResponse:
    """Mapper: Transform India Post API response to LocationResponse model."""
    post_office = api_data.get("PostOffice", [{}])[0]
    return LocationResponse(
        pincode=pincode,
        district=post_office.get("District", "Unknown"),
        city=post_office.get("Name", "Unknown"),
        state=post_office.get("State", "Unknown")
    )
