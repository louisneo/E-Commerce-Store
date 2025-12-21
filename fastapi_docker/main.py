import os
import sys
import django
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# ==========================================
# 1️⃣ Correct Django setup BEFORE importing Django modules
# ==========================================
# ⚠️ Update this path to point to your Django project root (where manage.py is located)
django_path = os.path.join(os.path.dirname(__file__), 'django_project')
sys.path.insert(0, django_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecom.settings")
django.setup()

# ==========================================
# 2️⃣ Import Django models AFTER setup
# ==========================================
from django.contrib.auth.models import User
from store.models import Product, CartItem, Customer
from payment.models import Order

# ==========================================
# 3️⃣ Initialize FastAPI app
# ==========================================
app = FastAPI(title="🛍️ Django + FastAPI E-commerce Integration")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 4️⃣ Pydantic Schemas
# ==========================================
class ProductSchema(BaseModel):
    id: int
    name: str
    price: float
    description: str | None = None

    class Config:
        from_attributes = True


class CartItemSchema(BaseModel):
    id: int
    product: ProductSchema
    quantity: int
    total_price: float

    class Config:
        orm_mode = True


class OrderSchema(BaseModel):
    id: int
    total: float
    status: str
    created_at: str

    class Config:
        orm_mode = True


# ==========================================
# 5️⃣ Routes
# ==========================================
@app.get("/")
def root():
    return {"message": "✅ FastAPI connected with Django successfully!"}


# Get all products
@app.get("/products", response_model=List[ProductSchema])
def get_products():
    products = Product.objects.all()
    return list(products)


# Get cart items by username
@app.get("/cart/{username}", response_model=List[CartItemSchema])
def get_cart(username: str):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    cart_items = CartItem.objects.filter(user=user)
    result = []
    for item in cart_items:
        result.append({
            "id": item.id,
            "product": item.product,
            "quantity": item.quantity,
            "total_price": float(item.product.price) * item.quantity,
        })
    return result


# Add item to cart
class AddToCart(BaseModel):
    username: str
    product_id: int
    quantity: int


@app.post("/cart/add")
def add_to_cart(data: AddToCart):
    try:
        user = User.objects.get(username=data.username)
        product = Product.objects.get(id=data.product_id)
    except (User.DoesNotExist, Product.DoesNotExist):
        raise HTTPException(status_code=404, detail="User or Product not found")

    cart_item, created = CartItem.objects.get_or_create(
        user=user,
        product=product,
        defaults={'quantity': data.quantity}
    )

    if not created:
        cart_item.quantity += data.quantity
        cart_item.save()

    return {"message": f"✅ Added {product.name} x{data.quantity} to {user.username}'s cart"}


# Remove item from cart
@app.delete("/cart/remove/{username}/{product_id}")
def remove_cart(username: str, product_id: int):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    deleted, _ = CartItem.objects.filter(user=user, product_id=product_id).delete()

    if deleted == 0:
        raise HTTPException(status_code=404, detail="Item not found in cart")

    return {"message": "🗑️ Item removed from cart"}

@app.get("/orders/{username}")
def get_orders(username: str):
    # 1️⃣ Check if the user exists
    user = User.objects.filter(username=username).first()
    if not user:
        raise HTTPException(status_code=404, detail="404: User not found")

    # 2️⃣ Get or create the related Customer record
    customer, created = Customer.objects.get_or_create(user=user)

    # 3️⃣ Fetch orders for this customer (if you have an Order model)
    orders = Order.objects.filter(customer=customer).select_related("product")

    # 4️⃣ Prepare JSON response
    orders_data = []
    for order in orders:
        orders_data.append({
            "id": order.id,
            "product": order.product.name if hasattr(order, "product") else None,
            "quantity": order.quantity,
            "total_price": float(order.total_price) if hasattr(order, "total_price") else None,
            "date_ordered": order.date_ordered.strftime("%Y-%m-%d %H:%M:%S") if hasattr(order, "date_ordered") else None,
        })

    # 5️⃣ Return result
    return {
        "username": username,
        "customer_created": created,
        "orders": orders_data
    }