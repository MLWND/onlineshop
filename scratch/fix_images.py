#!/usr/bin/env python
"""
TechMall 商品图片修复脚本
从 picsum.photos 下载占位图，确保所有种子商品都有图片显示
"""
import os
import sys
import django
import urllib.request
import ssl
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TechMall.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from Shop.models import Product


# 每个商品对应一个 picsum 的 seed ID，保证每次运行图片一致
PRODUCT_IMAGE_SEEDS = {
    "iPhone 17 Pro": 101,
    "Xiaomi 17 Ultra": 102,
    "Huawei Mate 80 Pro": 103,
    "OPPO Find X9 Ultra": 104,
    "vivo X300 Pro": 105,
    "MacBook Air M5": 201,
    "ThinkPad X1 Carbon Gen 14": 202,
    "Xiaomi Book Pro 16 2026": 203,
    "ROG Zephyrus G16 (2026)": 204,
    "Dell XPS 14 (2026)": 205,
    "AirPods Pro (3rd Gen)": 301,
    "Sony WH-1000XM6": 302,
    "Bose QuietComfort Ultra 2": 303,
    "Xiaomi Buds 6 Pro": 304,
    "Beats Studio Pro 2026": 305,
    "Apple Watch Series 11": 401,
    "Xiaomi Watch S5": 402,
    "Huawei Watch GT 6": 403,
    "Xiaomi Sound Ultra": 404,
    "DJI Osmo Pocket 4": 405,
}

MEDIA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media", "products")


def download_image(product_name, seed):
    """从 picsum.photos 下载一张 800x600 的占位图"""
    url = f"https://picsum.photos/seed/{seed}/800/600"
    safe_name = product_name.replace("/", "_").replace("(", "").replace(")", "")
    filename = f"{safe_name}.jpg"
    filepath = os.path.join(MEDIA_DIR, filename)

    if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
        return filename  # 已存在，跳过

    try:
        context = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15, context=context) as resp:
            data = resp.read()
            with open(filepath, "wb") as f:
                f.write(data)
            print(f"  [OK] {product_name} -> {filename} ({len(data)} bytes)")
            return filename
    except Exception as e:
        print(f"  [FAIL] {product_name}: {e}")
        return None


def main():
    print("=" * 50)
    print("  TechMall 商品图片修复")
    print("=" * 50)

    os.makedirs(MEDIA_DIR, exist_ok=True)

    products = Product.objects.all()
    updated = 0
    skipped = 0

    for p in products:
        # 已有有效图片则跳过
        if p.Image and os.path.exists(p.Image.path) and os.path.getsize(p.Image.path) > 1000:
            skipped += 1
            continue

        seed = PRODUCT_IMAGE_SEEDS.get(p.ProductName, hash(p.ProductName) % 900 + 100)
        filename = download_image(p.ProductName, seed)
        if filename:
            p.Image.name = f"products/{filename}"
            p.save(update_fields=["Image"])
            updated += 1
        time.sleep(0.3)  # 避免请求过快

    print(f"\n完成：更新 {updated} 张图片，跳过 {skipped} 张已有图片")


if __name__ == "__main__":
    main()
