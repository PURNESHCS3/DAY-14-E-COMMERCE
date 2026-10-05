import json
import os
import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Query,
)

from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.schemas import ProductCreate, ProductResponse
from app.dependencies import get_admin_user
from app.redis_client import redis_client


router = APIRouter(
    prefix="/api/products",
    tags=["Products"]
)


UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "uploads", "products")
)

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# ============================================================
# REDIS CACHE SETTINGS
# ============================================================

PRODUCT_CACHE_KEY = "products:all"

PRODUCT_CACHE_EXPIRE = 300  # 5 minutes


# ============================================================
# CREATE PRODUCT
# ============================================================

@router.post(
    "/",
    response_model=ProductResponse
)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_admin_user)
):

    product = Product(
        name=product_data.name,
        description=product_data.description,
        price=product_data.price,
        stock=product_data.stock
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    # Invalidate product cache
    redis_client.delete(PRODUCT_CACHE_KEY)

    return product


# ============================================================
# GET ALL PRODUCTS
# ============================================================

@router.get(
    "/",
    response_model=list[ProductResponse]
)
def get_products(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int | None = Query(None, ge=1, le=100),
):

    # --------------------------------------------------------
    # Check Redis cache
    # --------------------------------------------------------

    cached_products = redis_client.get(PRODUCT_CACHE_KEY) if limit is None else None

    if cached_products:

        print("PRODUCT CACHE HIT")

        return json.loads(cached_products)

    # --------------------------------------------------------
    # Cache miss → query PostgreSQL
    # --------------------------------------------------------

    print("PRODUCT CACHE MISS")

    products_query = db.query(Product).filter(Product.is_active == True)
    if limit is not None:
        products_query = products_query.order_by(Product.id).offset(skip).limit(limit)
    products = products_query.all()

    # --------------------------------------------------------
    # Convert SQLAlchemy objects to dictionaries
    # --------------------------------------------------------

    product_data = []

    for product in products:

        product_data.append({
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "stock": product.stock,
            "image_url": product.image_url,
            "is_active": product.is_active
        })

    # --------------------------------------------------------
    # Store result in Redis
    # --------------------------------------------------------

    if limit is None:
        redis_client.set(
            PRODUCT_CACHE_KEY,
            json.dumps(product_data),
            ex=PRODUCT_CACHE_EXPIRE
        )

    return product_data


# ============================================================
# GET PRODUCT BY ID
# ============================================================

@router.get(
    "/{product_id}",
    response_model=ProductResponse
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):

    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:

        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product


# ============================================================
# UPDATE PRODUCT
# ============================================================

@router.put(
    "/{product_id}",
    response_model=ProductResponse
)
def update_product(
    product_id: int,
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_admin_user)
):

    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:

        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    product.name = product_data.name
    product.description = product_data.description
    product.price = product_data.price
    product.stock = product_data.stock

    db.commit()
    db.refresh(product)

    # Invalidate product cache
    redis_client.delete(PRODUCT_CACHE_KEY)

    return product


# ============================================================
# DELETE PRODUCT
# ============================================================

@router.delete(
    "/{product_id}"
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_admin_user)
):

    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:

        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    product.is_active = False

    db.commit()

    # Invalidate product cache
    redis_client.delete(PRODUCT_CACHE_KEY)

    return {
        "message": "Product deleted successfully"
    }


# ============================================================
# UPLOAD PRODUCT IMAGE
# ============================================================

@router.post(
    "/{product_id}/image"
)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_admin_user)
):

    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:

        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    # --------------------------------------------------------
    # Allowed image types
    # --------------------------------------------------------

    allowed_types = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp"
    }

    if file.content_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail="Only JPEG, PNG and WebP images are allowed"
        )

    # --------------------------------------------------------
    # Generate unique filename
    # --------------------------------------------------------

    extension = allowed_types[file.content_type]

    filename = f"{uuid.uuid4()}.{extension}"

    filepath = os.path.join(
        UPLOAD_DIR,
        filename
    )

    # --------------------------------------------------------
    # Save file
    # --------------------------------------------------------

    content = await file.read()

    with open(filepath, "wb") as buffer:

        buffer.write(content)

    # --------------------------------------------------------
    # Save image URL
    # --------------------------------------------------------

    product.image_url = (
        f"/static/products/{filename}"
    )

    db.commit()
    db.refresh(product)

    # --------------------------------------------------------
    # Invalidate product cache
    # --------------------------------------------------------

    redis_client.delete(
        PRODUCT_CACHE_KEY
    )

    return {
        "message": "Image uploaded successfully",
        "image_url": product.image_url
    }