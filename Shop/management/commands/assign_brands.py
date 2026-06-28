"""
管理命令：将现有商品自动分配到对应品牌Agent
用法: python manage.py assign_brands
"""
from django.core.management.base import BaseCommand
from Shop.models import Product
from Simulation.models import BrandAgent


BRAND_KEYWORDS = {
    "Apple": ["Apple", "iPhone", "MacBook", "AirPods", "iPad", "Apple Watch"],
    "Xiaomi": ["Xiaomi", "小米", "Redmi", "Mi "],
    "Huawei": ["Huawei", "华为", "Honor", "Mate "],
    "Lenovo": ["Lenovo", "ThinkPad", "联想"],
}


class Command(BaseCommand):
    help = "将商品按名称关键词自动分配到对应的品牌Agent"

    def handle(self, *args, **options):
        brands = {b.brand_name: b for b in BrandAgent.objects.all()}
        if not brands:
            self.stderr.write("❌ 尚未初始化品牌Agent，请先访问 /simulation/init/")
            return

        assigned = 0
        for product in Product.objects.all():
            matched_brand = None
            for brand_name, keywords in BRAND_KEYWORDS.items():
                if brand_name not in brands:
                    continue
                for kw in keywords:
                    if kw.lower() in product.ProductName.lower():
                        matched_brand = brands[brand_name]
                        break
                if matched_brand:
                    break

            if matched_brand and product.brand != matched_brand:
                product.brand = matched_brand
                product.save(update_fields=["brand"])
                assigned += 1
                self.stdout.write(f"  [OK] {product.ProductName} -> {matched_brand.brand_name}")
            elif not matched_brand and not product.brand:
                self.stdout.write(f"  [--] {product.ProductName} -> Independent (no Agent)")

        self.stdout.write(self.style.SUCCESS(f"\n完成：{assigned} 件商品已分配品牌"))
