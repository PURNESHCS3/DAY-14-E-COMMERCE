from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import (
    auth,
    products,
    cart,
    orders,
    websocket
)


app = FastAPI(
    title="E-Commerce API",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(websocket.router)


def accepts_webp(accept_header: str) -> bool:
    for media_range in accept_header.split(","):
        media_type, *parameters = media_range.split(";")
        if media_type.strip() != "image/webp":
            continue

        quality = next(
            (
                parameter.split("=", 1)[1].strip()
                for parameter in parameters
                if parameter.strip().startswith("q=")
            ),
            "1",
        )
        try:
            return float(quality) > 0
        except ValueError:
            continue

    return False


@app.get("/static/products/{filename}", include_in_schema=False)
def serve_product_image(filename: str, request: Request):
    if Path(filename).name != filename:
        raise HTTPException(status_code=404, detail="Product image not found")

    image_path = Path(products.UPLOAD_DIR) / filename
    if not image_path.is_file():
        raise HTTPException(status_code=404, detail="Product image not found")

    webp_path = image_path.with_suffix(".webp")
    response_path = (
        webp_path
        if accepts_webp(request.headers.get("accept", "")) and webp_path.is_file()
        else image_path
    )

    return FileResponse(
        response_path,
        media_type="image/webp" if response_path == webp_path else None,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "Vary": "Accept",
        },
    )


app.mount(
    "/static/products",
    StaticFiles(directory=products.UPLOAD_DIR),
    name="product-images"
)