"""
ShopFlow — REST API 层（Sprint 2）

学习目标：
- 理解 HTTP 方法语义：GET/POST/PUT/DELETE 的幂等性
- 设计 RESTful URL（资源导向，名词而非动词）
- 理解 HTTP 状态码的语义（200/201/204/404/422）
- FastAPI 自动生成 OpenAPI 文档（访问 /docs）

运行方式：
    uvicorn shop.api:app --reload

测试方式：
    curl http://localhost:8000/products
    或访问 http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from shop.product_store import ProductStore, Product

app = FastAPI(
    title="ShopFlow API",
    description="Sprint 2 — 商品管理 REST API",
    version="0.1.0",
)


# ──────────────────────────────────────────
# 依赖注入：每个请求获取 Store 实例
# ──────────────────────────────────────────

def get_store() -> ProductStore:
    """依赖注入：返回 ProductStore 实例（测试时可替换）"""
    if not hasattr(app.state, "store"):
        app.state.store = ProductStore()
    return app.state.store


# ──────────────────────────────────────────
# Request / Response 模型
# ──────────────────────────────────────────

class ProductCreate(BaseModel):
    """POST /products 的请求体"""
    name: str = Field(..., min_length=1, max_length=200, examples=["Wireless Mouse"])
    price: float = Field(..., gt=0, examples=[29.99])
    stock: int = Field(..., ge=0, examples=[100])


class ProductUpdate(BaseModel):
    """PUT /products/{id} 的请求体（全部字段可选）"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)


class ProductResponse(BaseModel):
    """统一的商品响应格式"""
    id: int
    name: str
    price: float
    stock: int

    @classmethod
    def from_product(cls, p: Product) -> "ProductResponse":
        return cls(id=p.id, name=p.name, price=p.price, stock=p.stock)


# ──────────────────────────────────────────
# 端点定义
# ──────────────────────────────────────────

@app.get(
    "/products",
    response_model=list[ProductResponse],
    summary="获取所有商品",
)
def list_products(store: ProductStore = Depends(get_store)):
    """返回所有商品列表。"""
    return [ProductResponse.from_product(p) for p in store.list_all()]


@app.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="按 ID 获取商品",
)
def get_product(product_id: int, store: ProductStore = Depends(get_store)):
    """按 ID 查询单个商品。"""
    product = store.get_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"商品 {product_id} 不存在")
    return ProductResponse.from_product(product)


@app.post(
    "/products",
    response_model=ProductResponse,
    status_code=201,
    summary="创建商品",
)
def create_product(body: ProductCreate, store: ProductStore = Depends(get_store)):
    """创建新商品，返回带 ID 的商品对象。"""
    product = store.add(name=body.name, price=body.price, stock=body.stock)
    return ProductResponse.from_product(product)


@app.put(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="更新商品",
)
def update_product(product_id: int, body: ProductUpdate, store: ProductStore = Depends(get_store)):
    """更新商品字段（只更新请求体中非 None 的字段）。"""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        product = store.get_by_id(product_id)
        if product is None:
            raise HTTPException(status_code=404, detail=f"商品 {product_id} 不存在")
        return ProductResponse.from_product(product)

    updated = store.update(product_id, **updates)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"商品 {product_id} 不存在")
    return ProductResponse.from_product(updated)


@app.delete(
    "/products/{product_id}",
    status_code=204,
    summary="删除商品",
)
def delete_product(product_id: int, store: ProductStore = Depends(get_store)):
    """删除商品。成功返回 204，资源不存在返回 404。"""
    success = store.delete(product_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"商品 {product_id} 不存在")


@app.get(
    "/products/search/",
    response_model=list[ProductResponse],
    summary="按名称搜索商品",
)
def search_products(name: str, store: ProductStore = Depends(get_store)):
    """按名称关键词搜索商品（大小写不敏感）。"""
    results = store.search_by_name(name)
    return [ProductResponse.from_product(p) for p in results]
