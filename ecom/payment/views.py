from django.shortcuts import render, redirect
from payment.forms import ShippingForm, PaymentForm
from payment.models import ShippingAddress, Order, OrderItem
from django.contrib.auth.models import User
from cart.cart import Cart
from django.contrib import messages
from store.models import Product, Profile
import datetime
import requests


FASTAPI_URL = "http://127.0.0.1:8001" 

def orders(request, pk):
      if request.user.is_authenticated and request.user.is_superuser:
         order = Order.objects.get(id = pk)
         items = OrderItem.objects.filter(order = pk)

         if request.POST:
              status = request.POST['shipping_status']

              if status == "true":
                   order = Order.objects.filter(id = pk)
                   now = datetime.datetime.now()
                   order.update(shipped = True, date_shipped = now)
              else: 
                   order = Order.objects.filter(id = pk)
                   order.update(shipped = False)

              messages.success(request, "Shipping Status Updated")
              return redirect('home')
      
         return render(request, "payment/orders.html", {"order": order, "items": items})

def not_shipped_dash(request):
         
    if request.user.is_authenticated and request.user.is_superuser:
         orders = Order.objects.filter(shipped = False)

         if request.POST:
              status = request.POST['shipping_status']
              num = request.POST['num']

              order = Order.objects.filter(id = num)
              now = datetime.datetime.now()
              order.update(shipped = True, date_shipped = now)
      

              messages.success(request, "Shipping Status Updated")
              return redirect('home')

         return render(request, "payment/not_shipped_dash.html", {"orders": orders})
    else:
        messages.success(request, "Access Denied")
        return redirect('home')
        
def shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
         orders = Order.objects.filter(shipped = True)

         if request.POST:
              status = request.POST['shipping_status']
              num = request.POST['num']

              order = Order.objects.filter(id = num)
              now = datetime.datetime.now()
              order.update(shipped = False)
      

              messages.success(request, "Shipping Status Updated")
              return redirect('home')
         
         return render(request, "payment/shipped_dash.html", {"orders": orders})
    else:
        messages.success(request, "Access Denied")
        return redirect('home')

def process_order(request):
    if request.POST:
        cart = Cart(request)
        cart_products = cart.get_prods
        quantities = cart.get_quants
        totals = cart.cart_total()
        my_shipping = request.session.get('my_shipping')

        full_name = my_shipping['shipping_full_name']
        email = my_shipping['shipping_email']
        shipping_address = f"{my_shipping['shipping_address1']}\n{my_shipping['shipping_address2']}\n{my_shipping['shipping_city']}\n{my_shipping['shipping_state']}\n{my_shipping['shipping_zipcode']}\n{my_shipping['shipping_country']}"
        amount_paid = totals

        if request.user.is_authenticated:
            user = request.user
            create_order = Order(
                user=user,
                full_name=full_name,
                email=email,
                shipping_address=shipping_address,
                amount_paid=amount_paid
            )
            create_order.save()
            order_id = create_order.pk

            # Save each item to OrderItem
            for product in cart_products():
                product_id = product.id
                price = product.sale_price if product.is_sale else product.price
                for key, value in quantities().items():
                    if int(key) == product.id:
                        OrderItem.objects.create(
                            order_id=order_id,
                            product_id=product_id,
                            quantity=value,
                            price=price
                        )

            # 🔗 Sync to FastAPI backend
            try:
                order_payload = {
                    "user_id": user.id,
                    "full_name": full_name,
                    "email": email,
                    "shipping_address": shipping_address,
                    "amount_paid": amount_paid,
                    "items": [
                        {"product_id": p.id, "quantity": quantities()[str(p.id)], "price": float(p.price)}
                        for p in cart_products()
                    ]
                }
                requests.post(f"{FASTAPI_URL}/checkout", json=order_payload)
            except Exception as e:
                print("FastAPI order sync failed:", e)

            # Clear cart after checkout
            for key in list(request.session.keys()):
                if key == "session_key":
                    del request.session[key]
            Profile.objects.filter(user__id=request.user.id).update(old_cart="")
            
            # Clear CartItem from database after checkout
            from store.models import CartItem
            CartItem.objects.filter(user=request.user).delete()

            messages.success(request, "Order Placed!")
            return redirect('home')

        else:
            Order.objects.create(
                full_name=full_name,
                email=email,
                shipping_address=shipping_address,
                amount_paid=amount_paid
            )
            messages.success(request, "Order Placed!")
            return redirect('home')

    else:
        messages.success(request, "Access Denied")
        return redirect('home')

def billing_info(request):
    if request.POST:
        cart = Cart(request)
        cart_products = cart.get_prods
        quantities = cart.get_quants
        totals = cart.cart_total()

        my_shipping = request.POST
        request.session['my_shipping'] = my_shipping
        
        # Save or update shipping address for authenticated users
        if request.user.is_authenticated:
            try:
                # Try to get existing shipping address
                shipping_address = ShippingAddress.objects.get(user=request.user)
                # Update existing address
                shipping_address.shipping_full_name = my_shipping.get('shipping_full_name')
                shipping_address.shipping_email = my_shipping.get('shipping_email')
                shipping_address.shipping_address1 = my_shipping.get('shipping_address1')
                shipping_address.shipping_address2 = my_shipping.get('shipping_address2')
                shipping_address.shipping_city = my_shipping.get('shipping_city')
                shipping_address.shipping_state = my_shipping.get('shipping_state')
                shipping_address.shipping_zipcode = my_shipping.get('shipping_zipcode')
                shipping_address.shipping_country = my_shipping.get('shipping_country')
                shipping_address.save()
            except ShippingAddress.DoesNotExist:
                # Create new shipping address
                ShippingAddress.objects.create(
                    user=request.user,
                    shipping_full_name=my_shipping.get('shipping_full_name'),
                    shipping_email=my_shipping.get('shipping_email'),
                    shipping_address1=my_shipping.get('shipping_address1'),
                    shipping_address2=my_shipping.get('shipping_address2'),
                    shipping_city=my_shipping.get('shipping_city'),
                    shipping_state=my_shipping.get('shipping_state'),
                    shipping_zipcode=my_shipping.get('shipping_zipcode'),
                    shipping_country=my_shipping.get('shipping_country')
                )
        
        billing_form = PaymentForm()
        return render(request, "payment/billing_info.html", {
            "cart_products": cart_products,
            "quantities": quantities,
            "totals": totals,
            "shipping_info": request.POST,
            "billing_form": billing_form
        })
    else:
        messages.success(request, "Access Denied")
        return redirect('home')

# FIXED: Added try-except to handle missing ShippingAddress
def checkout(request):
    cart = Cart(request)
    cart_products = cart.get_prods
    quantities = cart.get_quants
    totals = cart.cart_total()
    
    if request.user.is_authenticated:
        try:
            # Try to get existing shipping address
            shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
            shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
        except ShippingAddress.DoesNotExist:
            # User doesn't have shipping address yet, create empty form
            shipping_form = ShippingForm(request.POST or None)
        
        return render(request, "payment/checkout.html", {
            "cart_products": cart_products,
            "quantities": quantities,
            "totals": totals,
            "shipping_form": shipping_form
        })
    else:
        # Guest checkout
        shipping_form = ShippingForm(request.POST or None)
        return render(request, "payment/checkout.html", {
            "cart_products": cart_products,
            "quantities": quantities,
            "totals": totals,
            "shipping_form": shipping_form
        })

def payment_success(request):
    return render(request, "payment/payment_success.html", {})