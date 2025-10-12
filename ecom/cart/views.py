from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import requests
from .cart import Cart

FASTAPI_URL = "http://127.0.0.1:8001"


@login_required
def cart_summary(request):
    from store.models import CartItem  # safe import

    cart_items = CartItem.objects.filter(user=request.user)
    cart_products = []
    totals = 0

    for item in cart_items:
        product = item.product
        total_price = float(product.sale_price if product.is_sale else product.price) * item.quantity

        cart_products.append({
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "sale_price": float(product.sale_price),
            "is_sale": product.is_sale,
            "description": product.description,
            "image": f"/media/{product.image}" if product.image else "",
            "quantity": item.quantity,
            "total": total_price,
        })
        totals += total_price

    quantities = {str(p["id"]): p["quantity"] for p in cart_products}

    return render(request, "cart_summary.html", {
        "cart_products": cart_products,
        "totals": totals,
        "quantities": quantities,
    })



@login_required
def cart_add(request):
    if request.POST.get("action") == "post":
        from store.models import Product, CartItem  # ✅ moved inside

        product_id = int(request.POST.get("product_id"))
        product_qty = int(request.POST.get("product_qty"))
        product = get_object_or_404(Product, id=product_id)

        cart = Cart(request)
        cart.add(product=product, quantity=product_qty)

        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={"quantity": product_qty},
        )
        if not created:
            cart_item.quantity += product_qty
            cart_item.save()

        # 🔗 Sync to FastAPI
        try:
            requests.post(f"{FASTAPI_URL}/cart/add", json={
                "user_id": request.user.id,
                "product_id": product_id,
                "quantity": product_qty,
            })
        except Exception as e:
            print("FastAPI sync failed:", e)

        messages.success(request, "Product added to cart...")
        return JsonResponse({"qty": cart_item.quantity})


@login_required
def cart_delete(request):
    if request.POST.get("action") == "post":
        from store.models import CartItem  # ✅ moved inside

        product_id = int(request.POST.get("product_id"))

        cart = Cart(request)
        cart.delete(product=product_id)
        CartItem.objects.filter(user=request.user, product_id=product_id).delete()

        try:
            requests.delete(f"{FASTAPI_URL}/cart/{request.user.id}/{product_id}")
        except Exception as e:
            print("FastAPI delete sync failed:", e)

        messages.success(request, "Item deleted from shopping cart...")
        return JsonResponse({"product": product_id})


@login_required
def cart_update(request):
    if request.POST.get("action") == "post":
        from store.models import CartItem  # ✅ moved inside

        product_id = int(request.POST.get("product_id"))
        product_qty = int(request.POST.get("product_qty"))

        cart = Cart(request)
        cart.update(product=product_id, quantity=product_qty)

        cart_item = CartItem.objects.get(user=request.user, product_id=product_id)
        cart_item.quantity = product_qty
        cart_item.save()

        try:
            requests.put(f"{FASTAPI_URL}/cart/update", json={
                "user_id": request.user.id,
                "product_id": product_id,
                "quantity": product_qty,
            })
        except Exception as e:
            print("FastAPI update sync failed:", e)

        messages.success(request, "Your cart has been updated...")
        return JsonResponse({"qty": product_qty})
