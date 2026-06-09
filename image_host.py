"""Lädt ein Bild zu imgbb hoch und gibt die öffentliche URL zurück."""
import base64
import requests

IMGBB_ENDPOINT = "https://api.imgbb.com/1/upload"

def upload_image(image_bytes: bytes, api_key: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    resp = requests.post(
        IMGBB_ENDPOINT,
        data={"key": api_key, "image": encoded},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["data"]["url"]
