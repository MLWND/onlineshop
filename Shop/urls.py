from django.urls import path

from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("category/<int:id>/", views.category, name="category"),
    path("brand/<int:id>/", views.brand_zone, name="brand_zone"),
    path("product/<int:id>/", views.productDetail, name="productDetail"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:id>/", views.addToCart, name="addToCart"),
    path("cart/delete/<int:id>/", views.deleteCart, name="deleteCart"),
    path("cart/increase/<int:id>/", views.increaseCart, name="increaseCart"),
    path("cart/decrease/<int:id>/", views.decreaseCart, name="decreaseCart"),
    path("order/submit/", views.submitOrder, name="submitOrder"),
    path("order/success/<int:id>/", views.orderSuccess, name="orderSuccess"),
]
