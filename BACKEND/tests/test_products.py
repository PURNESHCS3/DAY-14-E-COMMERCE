from pathlib import Path

from app.routers.products import UPLOAD_DIR


def test_create_product(
    client,
    admin_headers
):

    response = client.post(
        "/api/products/",
        headers=admin_headers,
        json={
            "name": "Laptop",
            "description": "Test laptop",
            "price": 50000,
            "stock": 10
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Laptop"
    assert data["stock"] == 10


def test_get_products(
    client,
    test_product
):

    response = client.get(
        "/api/products/"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) >= 1


def test_get_product(
    client,
    test_product
):

    response = client.get(
        f"/api/products/{test_product.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == test_product.id


def test_get_nonexistent_product(client):

    response = client.get(
        "/api/products/99999"
    )

    assert response.status_code == 404


def test_update_product(
    client,
    test_product,
    admin_headers
):

    response = client.put(
        f"/api/products/{test_product.id}",
        headers=admin_headers,
        json={
            "name": "Updated Product",
            "description": "Updated description",
            "price": 150,
            "stock": 30
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Updated Product"
    assert data["price"] == 150


def test_delete_product(
    client,
    test_product,
    admin_headers
):

    response = client.delete(
        f"/api/products/{test_product.id}",
        headers=admin_headers
    )

    assert response.status_code == 200

    data = response.json()

    assert "message" in data


def test_products_require_auth_for_modification(
    client,
    test_product
):

    response = client.put(
        f"/api/products/{test_product.id}",
        json={
            "name": "Unauthorized Update",
            "description": "Test",
            "price": 100,
            "stock": 10
        }
    )

    assert response.status_code == 401


def test_regular_users_cannot_modify_products(
    client,
    test_product,
    auth_headers
):

    payload = {
        "name": "Unauthorized Update",
        "description": "Test",
        "price": 100,
        "stock": 10
    }

    assert client.post(
        "/api/products/",
        headers=auth_headers,
        json=payload
    ).status_code == 403

    assert client.put(
        f"/api/products/{test_product.id}",
        headers=auth_headers,
        json=payload
    ).status_code == 403

    assert client.delete(
        f"/api/products/{test_product.id}",
        headers=auth_headers
    ).status_code == 403

    assert client.post(
        f"/api/products/{test_product.id}/image",
        headers=auth_headers,
        files={"file": ("image.png", b"test", "image/png")}
    ).status_code == 403


def test_frontend_origin_can_call_api(client):

    for origin in (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ):
        response = client.options(
            "/api/products/",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET"
            }
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_product_images_are_served(client):

    filename = "route-test-image.png"
    image_path = Path(UPLOAD_DIR) / filename
    image_path.write_bytes(b"test image content")

    try:
        response = client.get(f"/static/products/{filename}")
    finally:
        image_path.unlink(missing_ok=True)

    assert response.status_code == 200
    assert response.content == b"test image content"


def test_admin_can_upload_product_image(
    client,
    test_product,
    admin_headers
):

    response = client.post(
        f"/api/products/{test_product.id}/image",
        headers=admin_headers,
        files={"file": ("product.png", b"image content", "image/png")}
    )

    assert response.status_code == 200
    image_url = response.json()["image_url"]
    assert image_url.startswith("/static/products/")

    image_response = client.get(image_url)

    assert image_response.status_code == 200
    assert image_response.content == b"image content"

    image_path = Path(UPLOAD_DIR) / image_url.rsplit("/", 1)[-1]
    image_path.unlink(missing_ok=True)