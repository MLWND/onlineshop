import random
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Cart, Category, Order, OrderItem, Product


def cart_context(request):
    return {"cart_count": sum(item.Quantity for item in Cart.objects.all())}


def build_cart_summary():
    cart_items = list(Cart.objects.select_related("Product").all())
    total_amount = Decimal("0.00")
    for item in cart_items:
        item.subtotal_amount = item.Product.Price * item.Quantity
        total_amount += item.subtotal_amount
    return cart_items, total_amount


def generate_order_number():
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"TM{timestamp}{random.randint(1000, 9999)}"


def index(request):
    """商城首页 — 含品牌专区"""
    from Simulation.models import BrandAgent

    categories = Category.objects.all()
    # 只展示上架商品
    products = Product.objects.filter(is_active=True).select_related("Category", "brand")[:8]

    # 品牌专区数据
    brand_agents = BrandAgent.objects.all().order_by("-market_share")
    for ba in brand_agents:
        ba.active_product_count = Product.objects.filter(brand=ba, is_active=True).count()

    return render(request, "index.html", {
        "categories": categories,
        "products": products,
        "brand_agents": brand_agents,
    })


def category(request, id):
    category_obj = get_object_or_404(Category, id=id)
    products = Product.objects.filter(
        Category=category_obj, is_active=True
    ).select_related("Category", "brand")
    return render(request, "category.html", {"category": category_obj, "products": products})


def brand_zone(request, id):
    """品牌专区页 — 展示某品牌的所有商品 + Agent状态"""
    from Simulation.models import BrandAgent, BrandActionLog

    brand = get_object_or_404(BrandAgent, id=id)
    active_products = Product.objects.filter(brand=brand, is_active=True).select_related("Category")
    inactive_products = Product.objects.filter(brand=brand, is_active=False).select_related("Category")
    recent_actions = BrandActionLog.objects.filter(brand=brand).order_by("-day")[:5]

    context = {
        "brand": brand,
        "active_products": active_products,
        "inactive_products": inactive_products,
        "recent_actions": recent_actions,
    }
    return render(request, "brand_zone.html", context)


def productDetail(request, id):
    product = get_object_or_404(Product.objects.select_related("Category", "brand"), id=id)
    return render(request, "productDetail.html", {"product": product})


def addToCart(request, id):
    product = get_object_or_404(Product, id=id, is_active=True)
    cart_item, created = Cart.objects.get_or_create(Product=product, defaults={"Quantity": 1})
    if not created:
        cart_item.Quantity += 1
        cart_item.save(update_fields=["Quantity"])
    messages.success(request, f"{product.ProductName} 已加入购物车")
    return redirect("cart")


def cart(request):
    cart_items, total_amount = build_cart_summary()
    return render(request, "cart.html", {"cartItems": cart_items, "totalAmount": total_amount})


def deleteCart(request, id):
    cart_item = get_object_or_404(Cart, id=id)
    cart_item.delete()
    messages.success(request, "商品已从购物车移除")
    return redirect("cart")


def increaseCart(request, id):
    cart_item = get_object_or_404(Cart, id=id)
    cart_item.Quantity += 1
    cart_item.save(update_fields=["Quantity"])
    return redirect("cart")


def decreaseCart(request, id):
    cart_item = get_object_or_404(Cart, id=id)
    if cart_item.Quantity > 1:
        cart_item.Quantity -= 1
        cart_item.save(update_fields=["Quantity"])
    return redirect("cart")


def submitOrder(request):
    cart_items, total_amount = build_cart_summary()
    if not cart_items:
        messages.warning(request, "购物车为空，请先选择商品")
        return redirect("index")

    if request.method == "POST":
        payment_method = request.POST.get("paymentMethod", "支付宝")
        with transaction.atomic():
            order = Order.objects.create(TotalAmount=total_amount, PaymentMethod=payment_method)
            for item in cart_items:
                OrderItem.objects.create(
                    Order=order,
                    Product=item.Product,
                    Quantity=item.Quantity,
                    Price=item.Product.Price,
                )
                # ── 扣减库存 ──
                item.Product.Stock = max(0, item.Product.Stock - item.Quantity)
                item.Product.save(update_fields=["Stock"])

            Cart.objects.all().delete()

        # ── 真实用户购买计入模拟系统 ──
        _sync_order_to_simulation(order)

        return redirect("orderSuccess", id=order.id)

    context = {
        "cartItems": cart_items,
        "totalAmount": total_amount,
        "orderNumber": generate_order_number(),
        "paymentMethods": ["支付宝", "微信支付", "银行卡"],
    }
    return render(request, "orderSubmit.html", context)


def orderSuccess(request, id):
    order = get_object_or_404(Order, id=id)
    return render(request, "orderSuccess.html", {"order": order, "orderItems": order.items.select_related("Product")})


# ── 真实用户订单 → 模拟系统同步 ──

def _sync_order_to_simulation(order):
    """将真实用户订单数据同步到品牌Agent和每日统计"""
    from Simulation.models import BrandAgent, DailyStatistic, SimulationState

    current_day = SimulationState.get_instance().current_day
    order_profit = Decimal("0.00")

    for item in order.items.select_related("Product__brand"):
        brand = item.Product.brand
        cost_price = item.Product.CostPrice if item.Product.CostPrice > 0 else (item.Product.Price * Decimal("0.60"))
        item_revenue = item.Price * item.Quantity
        profit = (item.Price - cost_price) * item.Quantity
        order_profit += profit

        if brand:
            # 更新品牌累计数据和流动资金
            brand.total_sales += item.Quantity
            brand.total_revenue += item_revenue
            brand.funds += item_revenue
            brand.save(update_fields=["total_sales", "total_revenue", "funds"])
            
            # 同步更新品牌每日统计
            from Simulation.models import BrandDailyStatistic
            stat_obj, _ = BrandDailyStatistic.objects.get_or_create(
                brand=brand,
                day=current_day,
                defaults={
                    "sales_amount": Decimal("0.00"),
                    "profit_amount": Decimal("0.00"),
                    "order_count": 0
                }
            )
            stat_obj.sales_amount += item_revenue
            stat_obj.profit_amount += profit
            stat_obj.order_count += 1
            stat_obj.save(update_fields=["sales_amount", "profit_amount", "order_count"])

    # 更新当日统计（如有）
    stat = DailyStatistic.objects.filter(day=current_day).first()
    if stat:
        stat.total_sales += order.TotalAmount
        stat.total_profit += order_profit
        stat.order_count += 1
        stat.save(update_fields=["total_sales", "total_profit", "order_count"])
