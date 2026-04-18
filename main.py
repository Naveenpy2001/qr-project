from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer, CircleModuleDrawer, SquareModuleDrawer
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import re

app = FastAPI(title="QR Code Generator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STYLES = {
    "rounded": RoundedModuleDrawer,
    "circle": CircleModuleDrawer,
    "square": SquareModuleDrawer,
}

COLOR_PRESETS = {
    "midnight": {"fill": "#0F172A", "back": "#F8FAFC"},
    "violet":   {"fill": "#6D28D9", "back": "#F5F3FF"},
    "emerald":  {"fill": "#065F46", "back": "#ECFDF5"},
    "rose":     {"fill": "#9F1239", "back": "#FFF1F2"},
    "slate":    {"fill": "#334155", "back": "#F1F5F9"},
    "amber":    {"fill": "#92400E", "back": "#FFFBEB"},
}

def is_valid_url(url: str) -> bool:
    pattern = re.compile(
        r'^(https?://)'
        r'([a-zA-Z0-9\-\.]+)'
        r'(\.[a-zA-Z]{2,})'
        r'(:[0-9]+)?'
        r'(/[^\s]*)?$'
    )
    return bool(pattern.match(url))

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("index.html", "r") as f:
        return f.read()

@app.get("/generate")
async def generate_qr(
    url: str = Query(..., description="URL to encode"),
    style: str = Query("rounded", description="QR style: rounded, circle, square"),
    preset: str = Query("midnight", description="Color preset"),
    size: int = Query(300, ge=150, le=600, description="Output size in pixels"),
    format: str = Query("png", description="Output format: png or base64"),
):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if not is_valid_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL provided")

    style = style if style in STYLES else "rounded"
    colors = COLOR_PRESETS.get(preset, COLOR_PRESETS["midnight"])

    drawer_class = STYLES[style]

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=drawer_class(),
        fill_color=colors["fill"],
        back_color=colors["back"],
    )

    img = img.convert("RGBA")
    img = img.resize((size, size), Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)

    if format == "base64":
        encoded = base64.b64encode(buffer.read()).decode("utf-8")
        return {"image": f"data:image/png;base64,{encoded}", "url": url}

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="qrcode.png"'}
    )

@app.get("/presets")
async def get_presets():
    return {"presets": list(COLOR_PRESETS.keys()), "styles": list(STYLES.keys())}