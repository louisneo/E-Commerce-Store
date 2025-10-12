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
        cart = Cart(request)  # Initialize the cart object tied to the current session/request
        cart_products = cart.get_prods  # Get all products currently in the cart
        quantities = cart.get_quants  # Get corresponding quantities for each product
        totals = cart.cart_total()  # Calculate total price of all items in the cart

        my_shipping = request.POST
        request.session['my_shipping'] = my_shipping
        
        if request.user.is_authenticated:
              billing_form = PaymentForm()
              return render(request, "payment/billing_info.html", {
                    "cart_products": cart_products,
                    "quantities": quantities,
                    "totals": totals,
                    "shipping_info": request.POST,
                    "billing_form": billing_form
                })
        else:
                billing_form = PaymentForm()
                return render(request, "payment/billing_info.html", {
                        "cart_products": cart_products,
                        "quantities": quantities,
                        "totals": totals,
                        "shipping_info": request.POST,
                        "billing_form": billing_form
                    })

        shipping_form = request.POST
        return render(request, "payment/billing_info.html", {
                    "cart_products": cart_products,
                    "quantities": quantities,
                    "totals": totals,
                    "shipping_form": shipping_form
                })
    else:
         messages.success(request, "Access Denied")
         return redirect('home')

# Create your views here.
def checkout(request):
    cart = Cart(request)  # Initialize the cart object tied to the current session/request
    cart_products = cart.get_prods  # Get all products currently in the cart
    quantities = cart.get_quants  # Get corresponding quantities for each product
    totals = cart.cart_total()  # Calculate total price of all items in the cart
    
    if request.user.is_authenticated:
            shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
            
            shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
            return render(request, "payment/checkout.html", {
                "cart_products": cart_products,
                "quantities": quantities,
                "totals": totals,
                "shipping_form": shipping_form
            })

    else:
        shipping_form = ShippingForm(request.POST or None)
        return render(request, "payment/checkout.html", {
            "cart_products": cart_products,
            "quantities": quantities,
            "totals": totals,
            "shipping_form": shipping_form
        })

   

def payment_success(request):
    return render(request, "payment/payment_success.html", {})