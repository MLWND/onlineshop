import random
from decimal import Decimal

from django.db import models
from django.utils import timezone


class Category(models.Model):
    CategoryName = models.CharField("分类名称", max_length=100)
    Description = models.TextField("分类描述", blank=True)

    class Meta:
        verbose_name = "商品分类"
        verbose_name_plural = "商品分类"
        ordering = ["id"]

    def __str__(self):
        return self.CategoryName


class Product(models.Model):
    ProductName = models.CharField("商品名称", max_length=200)
    Category = models.ForeignKey(Category, verbose_name="所属分类", on_delete=models.CASCADE)
    Price = models.DecimalField("商品价格", max_digits=10, decimal_places=2)
    Stock = models.IntegerField("库存", default=0)
    Description = models.TextField("商品描述")
    Image = models.ImageField("商品图片", upload_to="products/", blank=True)
    brand = models.ForeignKey(
        "Simulation.BrandAgent", verbose_name="归属品牌",
        null=True, blank=True, on_delete=models.SET_NULL, related_name="products"
    )
    is_active = models.BooleanField("商城上架", default=True)
    Specs = models.JSONField("规格参数", default=dict, blank=True)
    PerformanceScore = models.IntegerField("性能评分", default=60)
    DesignScore = models.IntegerField("外观评分", default=60)
    UtilityScore = models.IntegerField("实用性评分", default=60)
    CostPrice = models.DecimalField("成本价(元)", max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = "商品"
        verbose_name_plural = "商品"
        ordering = ["-id"]

    def __str__(self):
        return self.ProductName

    @property
    def competitiveness_score(self):
        return round((self.PerformanceScore + self.DesignScore + self.UtilityScore) / 3)


class Cart(models.Model):
    Product = models.ForeignKey(Product, verbose_name="商品", on_delete=models.CASCADE)
    Quantity = models.IntegerField("数量", default=1)

    class Meta:
        verbose_name = "购物车"
        verbose_name_plural = "购物车"

    @property
    def subtotal(self):
        return self.Product.Price * self.Quantity

    def __str__(self):
        return f"{self.Product.ProductName} x {self.Quantity}"


class Order(models.Model):
    OrderNumber = models.CharField("订单编号", max_length=50, unique=True, blank=True)
    TotalAmount = models.DecimalField("总金额", max_digits=10, decimal_places=2, default=Decimal("0.00"))
    PaymentMethod = models.CharField("支付方式", max_length=20)
    CreateTime = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "订单"
        verbose_name_plural = "订单"
        ordering = ["-CreateTime"]

    def save(self, *args, **kwargs):
        if not self.OrderNumber:
            timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
            self.OrderNumber = f"TM{timestamp}{random.randint(1000, 9999)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.OrderNumber


class OrderItem(models.Model):
    Order = models.ForeignKey(Order, verbose_name="所属订单", related_name="items", on_delete=models.CASCADE)
    Product = models.ForeignKey(Product, verbose_name="商品", on_delete=models.CASCADE)
    Quantity = models.IntegerField("数量")
    Price = models.DecimalField("下单单价", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "订单详情"
        verbose_name_plural = "订单详情"

    @property
    def subtotal(self):
        return self.Price * self.Quantity

    def __str__(self):
        return f"{self.Order.OrderNumber} - {self.Product.ProductName}"
