"""
Sprint 2 API 测试

运行：pytest tests/test_api.py -v

学习目标：
- 理解 HTTP 状态码的语义
- 验证 RESTful API 的幂等性
- 用 httpx.AsyncClient 测试 FastAPI
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from shop.api import app, get_store
from shop.product_store import ProductStore


@pytest_asyncio.fixture
async def client(tmp_path):
    """异步 HTTP 客户端，每个测试用独立的 ProductStore"""
    # 为每个测试创建独立的 store（使用临时文件）
    data_file = str(tmp_path / "products.json")
    test_store = ProductStore(data_file=data_file)

    # 覆盖 app 的依赖注入
    app.dependency_overrides[get_store] = lambda: test_store

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # 清理依赖覆盖
    app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestProductAPI:
    async def test_list_empty(self, client):
        """GET /products 空列表返回 200"""
        response = await client.get("/products")
        assert response.status_code == 200
        assert response.json() == []

    async def test_create_product(self, client):
        """POST /products 创建商品返回 201"""
        response = await client.post(
            "/products",
            json={"name": "Widget", "price": 9.99, "stock": 100},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Widget"
        assert data["price"] == 9.99

    async def test_get_product(self, client):
        """GET /products/{id} 返回 200"""
        # 先创建
        create_resp = await client.post(
            "/products", json={"name": "Gadget", "price": 19.99, "stock": 50}
        )
        product_id = create_resp.json()["id"]

        # 再查询
        response = await client.get(f"/products/{product_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Gadget"

    async def test_get_nonexistent_returns_404(self, client):
        """GET /products/999 不存在返回 404"""
        response = await client.get("/products/999")
        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]

    async def test_update_product(self, client):
        """PUT /products/{id} 更新返回 200"""
        create_resp = await client.post(
            "/products", json={"name": "Widget", "price": 9.99, "stock": 100}
        )
        product_id = create_resp.json()["id"]

        response = await client.put(
            f"/products/{product_id}", json={"price": 12.99}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["price"] == 12.99
        assert data["name"] == "Widget"  # 未修改字段保持不变

    async def test_update_is_idempotent(self, client):
        """PUT 幂等性：多次调用结果相同"""
        create_resp = await client.post(
            "/products", json={"name": "Widget", "price": 9.99, "stock": 100}
        )
        product_id = create_resp.json()["id"]

        # 第一次更新
        resp1 = await client.put(f"/products/{product_id}", json={"price": 15.0})
        # 第二次更新（相同请求）
        resp2 = await client.put(f"/products/{product_id}", json={"price": 15.0})

        assert resp1.status_code == resp2.status_code == 200
        assert resp1.json()["price"] == resp2.json()["price"] == 15.0

    async def test_delete_product(self, client):
        """DELETE /products/{id} 成功返回 204"""
        create_resp = await client.post(
            "/products", json={"name": "Widget", "price": 9.99, "stock": 100}
        )
        product_id = create_resp.json()["id"]

        response = await client.delete(f"/products/{product_id}")
        assert response.status_code == 204
        assert response.content == b""  # 204 无响应体

        # 验证已删除
        get_resp = await client.get(f"/products/{product_id}")
        assert get_resp.status_code == 404

    async def test_delete_is_idempotent(self, client):
        """DELETE 幂等性：删除已删除的资源返回 404（结果一致：资源不存在）"""
        create_resp = await client.post(
            "/products", json={"name": "Widget", "price": 9.99, "stock": 100}
        )
        product_id = create_resp.json()["id"]

        # 第一次删除
        resp1 = await client.delete(f"/products/{product_id}")
        assert resp1.status_code == 204

        # 第二次删除（资源已不存在）
        resp2 = await client.delete(f"/products/{product_id}")
        assert resp2.status_code == 404

    async def test_search_products(self, client):
        """GET /products/search/?name=xxx 搜索"""
        await client.post("/products", json={"name": "Wireless Mouse", "price": 29.99, "stock": 50})
        await client.post("/products", json={"name": "Wired Keyboard", "price": 49.99, "stock": 30})

        response = await client.get("/products/search/?name=wireless")
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["name"] == "Wireless Mouse"

    async def test_create_invalid_data_returns_422(self, client):
        """POST 请求体不合法返回 422 Unprocessable Entity"""
        response = await client.post(
            "/products",
            json={"name": "", "price": -10, "stock": 100},  # name 空，price 负数
        )
        assert response.status_code == 422  # FastAPI 自动验证
