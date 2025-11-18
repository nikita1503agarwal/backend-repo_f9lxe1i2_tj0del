"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection

These schemas are used by the backend API for validation and by the
built-in database tools for management.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl

# ---------- Core Commerce Schemas ----------

Gender = Literal["women", "men", "kids"]
ProductType = Literal["tops", "bottoms", "dress", "shoes"]

class Category(BaseModel):
    name: str = Field(..., description="Display name")
    slug: str = Field(..., description="URL-friendly id")
    gender: Gender = Field(..., description="Target gender segment")

class ProductImage(BaseModel):
    url: HttpUrl
    alt: Optional[str] = None

class Variant(BaseModel):
    sku: str
    size: Optional[str] = Field(None, description="Size or EU/US shoe size")
    color: Optional[str] = None
    stock: int = Field(0, ge=0)

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    currency: str = Field("USD")
    gender: Gender
    type: ProductType
    category: str = Field(..., description="Category slug")
    tags: List[str] = Field(default_factory=list)
    images: List[ProductImage] = Field(default_factory=list)
    variants: List[Variant] = Field(default_factory=list)
    featured: bool = False

class CartItem(BaseModel):
    product_id: str
    sku: str
    quantity: int = Field(1, ge=1)

class Cart(BaseModel):
    session_id: str
    items: List[CartItem] = Field(default_factory=list)

# You can extend with User/Order later as needed.
