#!/usr/bin/env python
"""
TechMall 推演数据重置脚本
将模拟系统彻底还原至 Day 1 初始状态：
- 天数归 1
- 清空所有顾客、重新播种 10 名种子顾客
- 4 个品牌资金重置为 100,000 元，清零累计统计，解除破产
- 清空所有模拟订单（Order + OrderItem）
- 清空 MarketEvent / DailyStatistic / BrandActionLog / DailyReport / BrandDailyStatistic
- 删除 AI 发布的新品，保留初始 20 款商品并恢复默认库存
"""

import os
import sys
import shutil
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TechMall.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from decimal import Decimal
from django.core.management import call_command
from Shop.models import Product, Order, OrderItem, Category
from Simulation.views import _assign_products_to_brands
from Simulation.models import (
    SimulationState,
    BrandAgent,
    CustomerAgent,
    MarketEvent,
    DailyStatistic,
    BrandActionLog,
    DailyReport,
    BrandDailyStatistic,
)


def reset_all():
    print("=" * 50)
    print("  TechMall 推演数据重置")
    print("=" * 50)

    # ── 1. 清空所有模拟订单 ──
    oi_count, _ = OrderItem.objects.all().delete()
    o_count, _ = Order.objects.all().delete()
    print(f"[1] 订单已清空：{o_count} 条订单，{oi_count} 条订单项")

    # ── 2. 清空所有模拟日志 ──
    dr_count, _ = DailyReport.objects.all().delete()
    bds_count, _ = BrandDailyStatistic.objects.all().delete()
    me_count, _ = MarketEvent.objects.all().delete()
    ds_count, _ = DailyStatistic.objects.all().delete()
    bal_count, _ = BrandActionLog.objects.all().delete()
    print(f"[2] 模拟日志已清空：日报{dr_count} / 品牌日统计{bds_count} / 事件{me_count} / 每日汇总{ds_count} / 行动日志{bal_count}")

    # ── 3. 删除所有商品，从 fixture 重新加载种子商品 ──
    p_count = Product.objects.count()
    Product.objects.all().delete()
    Category.objects.all().delete()
    call_command("loaddata", "Shop/fixtures/initial_data.json")
    restored = Product.objects.count()
    print(f"[3] 商品已重置：删除 {p_count} 件，从 fixture 恢复 {restored} 件种子商品")

    # ── 3a. 复制种子商品图片到 media/products/ ──
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    image_src = os.path.join(project_root, "image")
    media_dst = os.path.join(project_root, "media", "products")
    os.makedirs(media_dst, exist_ok=True)
    copied = 0
    if os.path.isdir(image_src):
        for fname in os.listdir(image_src):
            if fname.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                src = os.path.join(image_src, fname)
                dst = os.path.join(media_dst, fname)
                shutil.copy2(src, dst)
                copied += 1
    print(f"[3a] 商品图片已复制：{copied} 张 from image/ -> media/products/")

    # 恢复种子商品的库存和上架状态，并修正图片路径
    DEFAULT_STOCK = {"手机": 50, "电脑": 30, "耳机": 80, "智能设备": 60}
    # 数据库可能保存旧文件名（无括号），修正为实际文件名
    IMAGE_NAME_FIXES = {
        "AirPods Pro 3rd Gen.jpg": "AirPods Pro (3rd Gen).jpg",
        "Dell XPS 14 2026.jpg": "Dell XPS 14 (2026).jpg",
        "ROG Zephyrus G16 2026.jpg": "ROG Zephyrus G16 (2026).jpg",
    }
    for p in Product.objects.all():
        cat_name = p.Category.CategoryName
        stock = 50
        for key, val in DEFAULT_STOCK.items():
            if key in cat_name:
                stock = val
                break
        # 修正图片文件名
        if p.Image:
            basename = os.path.basename(p.Image.name)
            if basename in IMAGE_NAME_FIXES:
                p.Image.name = f"products/{IMAGE_NAME_FIXES[basename]}"
        p.Stock = stock
        p.is_active = True
        p.save(update_fields=["Stock", "is_active", "Image"])
    print(f"[3b] 种子商品库存已恢复：{restored} 件")

    # ── 4. 重置品牌 Agent ──
    BRAND_DEFAULTS = {
        "Apple":   {"strategy": "premium",   "reputation": 75.0, "aggressiveness": 0.3, "target_sales": 10, "logo_emoji": "🍎", "color": "#555555"},
        "Xiaomi":  {"strategy": "aggressive", "reputation": 70.0, "aggressiveness": 0.7, "target_sales": 15, "logo_emoji": "📱", "color": "#FF6700"},
        "Huawei":  {"strategy": "branding",  "reputation": 72.0, "aggressiveness": 0.5, "target_sales": 12, "logo_emoji": "🔵", "color": "#CF0A2C"},
        "Lenovo":  {"strategy": "stable",    "reputation": 68.0, "aggressiveness": 0.4, "target_sales": 10, "logo_emoji": "💻", "color": "#E2231A"},
    }
    for b in BrandAgent.objects.all():
        defaults = BRAND_DEFAULTS.get(b.brand_name, {})
        b.funds = Decimal("100000.00")
        b.is_bankrupt = False
        b.total_sales = 0
        b.total_revenue = Decimal("0")
        b.market_share = 25.0
        b.reputation = defaults.get("reputation", 70.0)
        b.aggressiveness = defaults.get("aggressiveness", 0.5)
        b.strategy = defaults.get("strategy", "stable")
        b.target_sales = defaults.get("target_sales", 10)
        b.save()
    print(f"[4] 品牌 Agent 已重置：资金 100,000 元，累计统计清零")

    # ── 5. 清空顾客，重新播种 10 名种子顾客 ──
    CustomerAgent.objects.all().delete()
    SEED_CUSTOMERS = [
        {"name": "张伟",   "age": 28, "occupation": "engineer",   "budget": 8000,  "preference": "gaming",    "loyalty": 0.6, "activity": 0.8},
        {"name": "李芳",   "age": 24, "occupation": "white_collar", "budget": 5000, "preference": "office",   "loyalty": 0.5, "activity": 0.7},
        {"name": "王强",   "age": 31, "occupation": "executive",  "budget": 15000, "preference": "high_end",  "loyalty": 0.7, "activity": 0.6},
        {"name": "刘洋",   "age": 21, "occupation": "student",    "budget": 2000,  "preference": "student",   "loyalty": 0.3, "activity": 0.9},
        {"name": "陈静",   "age": 26, "occupation": "freelancer", "budget": 6000,  "preference": "budget",    "loyalty": 0.5, "activity": 0.75},
        {"name": "赵磊",   "age": 29, "occupation": "engineer",   "budget": 10000, "preference": "high_end",  "loyalty": 0.65, "activity": 0.7},
        {"name": "周敏",   "age": 22, "occupation": "student",    "budget": 1500,  "preference": "budget",    "loyalty": 0.4, "activity": 0.85},
        {"name": "黄鑫",   "age": 33, "occupation": "white_collar", "budget": 7000, "preference": "office",  "loyalty": 0.55, "activity": 0.65},
        {"name": "林宇",   "age": 27, "occupation": "freelancer", "budget": 4500,  "preference": "gaming",    "loyalty": 0.45, "activity": 0.8},
        {"name": "孙浩",   "age": 35, "occupation": "executive",  "budget": 20000, "preference": "high_end",  "loyalty": 0.75, "activity": 0.55},
    ]
    for c in SEED_CUSTOMERS:
        CustomerAgent.objects.create(**c)
    print(f"[5] 顾客已重置：清空后播种 {len(SEED_CUSTOMERS)} 名种子顾客")

    # ── 6. 重置模拟天数至 Day 1 ──
    state = SimulationState.get_instance()
    state.current_day = 1
    state.save(update_fields=["current_day"])
    print(f"[6] 模拟天数已重置为 Day 1")

    # ── 7. 自动分配商品到品牌 ──
    _assign_products_to_brands()

    print("=" * 50)
    print("  [OK] 重置完成！数据已还原至初始 Day 1 状态")
    print("=" * 50)


if __name__ == "__main__":
    confirm = input("确认重置所有推演数据至 Day 1？(y/N): ").strip().lower()
    if confirm == "y":
        reset_all()
    else:
        print("已取消。")
