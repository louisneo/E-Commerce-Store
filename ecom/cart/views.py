from django.shortcuts import render, get_object_or_404
from .cart import Cart
from store.models import Product, CartItem
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# Display cart summary (from database)
@login_required
def cart_summary(request):
    cart_items = CartItem.objects.filter(user=request.user)
    cart_products = []
    totals = 0

    for item in cart_items:
        total_price = float(item.product.price) * item.quantity
        cart_products.append({
            "id": item.product.id,
            "name": item.product.name,
            "price": float(item.product.price),
            "quantity": item.quantity,
            "total": total_price
        })
        totals += total_price

    return render(request, "cart_summary.html", {
        "cart_products": cart_products,
        "totals": totals
    })

# Add product to cart
@login_required
def cart_add(request):
    if request.POST.get('action') == 'post':
        product_id = int(request.POST.get('product_id'))
        product_qty = int(request.POST.get('product_qty'))

        product = get_object_or_404(Product, id=product_id)

        # Add to session cart
        cart = Cart(request)
        cart.add(product=product, quantity=product_qty)

        # Add to database cart
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'quantity': product_qty}
        )
        if not created:
            cart_item.quantity += product_qty
            cart_item.save()

        messages.success(request, "Product added to cart...")
        return JsonResponse({'qty': cart_item.quantity})

# Delete product from cart
@login_required
def cart_delete(request):
    if request.POST.get('action') == 'post':
        product_id = int(request.POST.get('product_id'))

        cart = Cart(request)
        cart.delete(product=product_id)

        # Delete from DB
        CartItem.objects.filter(user=request.user, product_id=product_id).delete()
        messages.success(request, "Item deleted from shopping cart...")

        return JsonResponse({'product': product_id})

# Update product quantity in cart
@login_required
def cart_update(request):
    if request.POST.get('action') == 'post':
        product_id = int(request.POST.get('product_id'))
        product_qty = int(request.POST.get('product_qty'))

        cart = Cart(request)
        cart.update(product=product_id, quantity=product_qty)

        # Update in DB
        cart_item = CartItem.objects.get(user=request.user, product_id=product_id)
        cart_item.quantity = product_qty
        cart_item.save()

        messages.success(request, "Your cart has been updated...")
        return JsonResponse({'qty': product_qty})
