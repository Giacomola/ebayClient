from unittest.mock import patch, MagicMock
from image_host import upload_image

def test_upload_image_gibt_url_zurueck():
    fake = MagicMock()
    fake.json.return_value = {"data": {"url": "https://i.ibb.co/abc/1.jpg"}}
    fake.raise_for_status.return_value = None
    with patch("image_host.requests.post", return_value=fake) as post:
        url = upload_image(b"\xff\xd8fakejpeg", "imgbb-key")
    assert url == "https://i.ibb.co/abc/1.jpg"
    assert post.call_args.kwargs["data"]["key"] == "imgbb-key"
