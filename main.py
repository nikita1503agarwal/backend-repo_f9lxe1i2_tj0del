import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Category, Cart, CartItem

app = FastAPI(title="Luxury Store API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Helpers ----------

def oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")

# ---------- Health ----------

@app.get("/")
def root():
    return {"message": "Luxury Store API running"}

@app.get("/test")
def test_database():
    resp = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "collections": []
    }
    try:
        if db is not None:
            resp["database"] = "✅ Connected"
            resp["database_url"] = "✅ Set"
            resp["database_name"] = db.name
            resp["collections"] = db.list_collection_names()
    except Exception as e:
        resp["database"] = f"⚠️ {str(e)[:80]}"
    return resp

# ---------- Seed Data ----------

class SeedRequest(BaseModel):
    force: bool = False

@app.post("/api/seed")
def seed(req: SeedRequest):
    # Only seed if empty or force=True
    if not req.force:
        if db["category"].estimated_document_count() > 0 and db["product"].estimated_document_count() > 0:
            return {"status": "ok", "message": "Already seeded"}

    db["category"].delete_many({})
    db["product"].delete_many({})

    categories = [
        {"name": "Women", "slug": "women", "gender": "women"},
        {"name": "Men", "slug": "men", "gender": "men"},
        {"name": "Kids", "slug": "kids", "gender": "kids"},
    ]

    for c in categories:
        create_document("category", c)

    sample_products = [
        {
            "title": "Silk Emerald Top",
            "description": "Silk satin blouse with subtle sheen.",
            "price": 890.0,
            "currency": "USD",
            "gender": "women",
            "type": "tops",
            "category": "women",
            "tags": ["seasonal", "emerald"],
            "images": [
                {"url": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab", "alt": "Silk Top"}
            ],
            "variants": [
                {"sku": "W-TOP-EMR-S", "size": "S", "stock": 5},
                {"sku": "W-TOP-EMR-M", "size": "M", "stock": 7},
                {"sku": "W-TOP-EMR-L", "size": "L", "stock": 4},
            ],
            "featured": True,
        },
        {
            "title": "Tailored Wool Trousers",
            "description": "Slim fit wool trousers with pressed creases.",
            "price": 760.0,
            "currency": "USD",
            "gender": "men",
            "type": "bottoms",
            "category": "men",
            "tags": ["classic"],
            "images": [
                {"url": "https://images.unsplash.com/photo-1520975693416-35a1d9d8f5f4", "alt": "Wool Trousers"}
            ],
            "variants": [
                {"sku": "M-BOT-WOOL-30", "size": "30", "stock": 6},
                {"sku": "M-BOT-WOOL-32", "size": "32", "stock": 8},
            ],
            "featured": True,
        },
        {
            "title": "Kid's Party Dress",
            "description": "Tulle skirt with satin bodice in amber accents.",
            "price": 520.0,
            "currency": "USD",
            "gender": "kids",
            "type": "dress",
            "category": "kids",
            "tags": ["seasonal", "gold"],
            "images": [
                {"url": "https://images.unsplash.com/photo-1520975236143-0f2a8f3f6b9a", "alt": "Kids Dress"}
            ],
            "variants": [
                {"sku": "K-DRS-PT-4", "size": "4", "stock": 10},
                {"sku": "K-DRS-PT-6", "size": "6", "stock": 7},
            ],
            "featured": True,
        },
        {
            "title": "Calf Leather Oxfords",
            "description": "Hand-polished leather shoes with amber lining.",
            "price": 980.0,
            "currency": "USD",
            "gender": "men",
            "type": "shoes",
            "category": "men",
            "tags": ["new"],
            "images": [
                {"url": "https://images.unsplash.com/photo-1515542706656-8e6ef17a1521", "alt": "Leather Oxfords"}
            ],
            "variants": [
                {"sku": "M-SHO-OXF-42", "size": "42", "stock": 3},
                {"sku": "M-SHO-OXF-43", "size": "43", "stock": 2},
            ],
            "featured": False,
        },
    ]

    for p in sample_products:
        create_document("product", p)

    return {"status": "ok", "seeded": len(sample_products)}

# ---------- Categories ----------

@app.get("/api/categories")
def list_categories():
    return get_documents("category")

# ---------- Products ----------

@app.get("/api/products")
def list_products(
    gender: Optional[str] = None,
    type: Optional[str] = Query(None, alias="ptype"),
    category: Optional[str] = None,
    featured: Optional[bool] = None,
    q: Optional[str] = None,
):
    filt = {}
    if gender:
        filt["gender"] = gender
    if type:
        filt["type"] = type
    if category:
        filt["category"] = category
    if featured is not None:
        filt["featured"] = featured
    if q:
        filt["title"] = {"$regex": q, "$options": "i"}
    return get_documents("product", filt)

@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    doc = db["product"].find_one({"_id": oid(product_id)})
    if not doc:
        raise HTTPException(404, "Product not found")
    return doc

# ---------- Cart ----------

@app.post("/api/cart")
def create_or_get_cart(cart: Cart):
    existing = db["cart"].find_one({"session_id": cart.session_id})
    if not existing:
        create_document("cart", cart.dict())
        existing = db["cart"].find_one({"session_id": cart.session_id})
    return existing

class UpdateCartRequest(BaseModel):
    session_id: str
    item: CartItem

@app.post("/api/cart/add")
def cart_add(req: UpdateCartRequest):
    cart = db["cart"].find_one({"session_id": req.session_id})
    if not cart:
        create_document("cart", {"session_id": req.session_id, "items": []})
        cart = db["cart"].find_one({"session_id": req.session_id})

    items = cart.get("items", [])
    found = False
    for it in items:
        if it["sku"] == req.item.sku:
            it["quantity"] += req.item.quantity
            found = True
            break
    if not found:
        items.append(req.item.dict())

    db["cart"].update_one({"_id": cart["_id"]}, {"$set": {"items": items}})
    updated = db["cart"].find_one({"_id": cart["_id"]})
    return updated

@app.post("/api/cart/remove")
def cart_remove(req: UpdateCartRequest):
    cart = db["cart"].find_one({"session_id": req.session_id})
    if not cart:
        raise HTTPException(404, "Cart not found")
    items = [it for it in cart.get("items", []) if it["sku"] != req.item.sku]
    db["cart"].update_one({"_id": cart["_id"]}, {"$set": {"items": items}})
    return db["cart"].find_one({"_id": cart["_id"]})

# ---------- Search ----------

@app.get("/api/search")
def search_products(q: str = Query("")):
    if not q:
        return []
    return list(db["product"].find({"title": {"$regex": q, "$options": "i"}}).limit(10))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
