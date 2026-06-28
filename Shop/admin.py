from django.contrib import admin

from .models import Cart, Category, Order, OrderItem, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "CategoryName", "Description")
    search_fields = ("CategoryName",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "ProductName", "Category", "brand", "Price", "Stock", "is_active")
    list_filter = ("Category", "brand", "is_active")
    search_fields = ("ProductName", "Description")
    list_editable = ("is_active",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "Product", "Quantity", "subtotal")
    search_fields = ("Product__ProductName",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "OrderNumber", "TotalAmount", "PaymentMethod", "CreateTime")
    list_filter = ("PaymentMethod", "CreateTime")
    search_fields = ("OrderNumber",)
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "Order", "Product", "Quantity", "Price", "subtotal")
    search_fields = ("Order__OrderNumber", "Product__ProductName")
