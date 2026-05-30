import base64
from io import BytesIO

import qrcode


def generate_qr_data_url(text: str) -> str:
    img = qrcode.make(text)
    bio = BytesIO()
    img.save(bio, format="PNG")
    b64 = base64.b64encode(bio.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"
