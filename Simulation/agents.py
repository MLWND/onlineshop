"""
AI电商生态模拟平台 — Agent 逻辑核心
包含四个Agent：市场Agent、品牌Agent、顾客Agent、AI分析Agent
以及主控函数 advance_day()
"""
import base64
import json
import logging
import os
import random
from decimal import Decimal

import urllib.request
import urllib.error

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from Shop.models import Category, Order, OrderItem, Product
from .models import (
    BrandActionLog,
    BrandAgent,
    CustomerAgent,
    DailyReport,
    DailyStatistic,
    MarketEvent,
    SimulationState,
    BrandDailyStatistic,
)

logger = logging.getLogger(__name__)

import threading
_advance_day_lock = threading.Lock()


# ══════════════════════════════════════════════════════
#  工具函数
# ══════════════════════════════════════════════════════

def _get_current_day() -> int:
    return SimulationState.get_instance().current_day


def _clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))


def _search_web(query: str) -> str:
    """
    轻量级免Key网络搜索函数，查询 DuckDuckGo 并解析摘要
    """
    import urllib.request
    import urllib.parse
    import re
    import ssl

    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    try:
        context = ssl._create_unverified_context()
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        )
        with urllib.request.urlopen(req, timeout=12, context=context) as resp:
            html = resp.read().decode("utf-8")
            snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
            if snippets:
                cleaned = []
                for s in snippets[:4]:
                    clean_s = re.sub(r'<[^>]*>', '', s).strip()
                    cleaned.append(clean_s)
                return "\n".join(cleaned)
    except Exception as e:
        logger.warning(f"[Search] Web search failed for query '{query}': {e}")
    return ""


def _calibrate_price_via_search(brand_name: str, product_line: str, category_name: str) -> tuple:
    """
    联网价格校准：联网搜索特定品类商品的真实价格，返回 (calibrated_price, cost_price)
    如果未搜索到或异常，返回 (None, None)
    """
    import re
    query = f"{brand_name} {product_line} 价格 售价 RMB 元"
    logger.info(f"[PriceCalibration] Searching web for query: '{query}'")
    search_results = _search_web(query)
    
    if not search_results:
        return None, None

    # 匹配 ¥999, 999元, 999.00元, 999 CNY, 999 Yuan 等
    patterns = [
        r'¥\s*([1-9]\d{1,5}(?:\.\d{2})?)',
        r'([1-9]\d{1,5}(?:\.\d{2})?)\s*元',
        r'([1-9]\d{1,5}(?:\.\d{2})?)\s*CNY',
        r'([1-9]\d{1,5}(?:\.\d{2})?)\s*Yuan',
        r'([1-9]\d{1,5}(?:\.\d{2})?)\s*yuan',
    ]
    
    extracted_prices = []
    for pat in patterns:
        matches = re.findall(pat, search_results)
        for m in matches:
            try:
                price_val = float(m)
                extracted_prices.append(price_val)
            except ValueError:
                pass

    if not extracted_prices:
        return None, None

    c_name = category_name.lower()
    if "手机" in c_name or "phone" in c_name:
        p_min, p_max = 400.0, 18000.0
    elif "电脑" in c_name or "computer" in c_name or "laptop" in c_name:
        p_min, p_max = 1800.0, 32000.0
    elif "耳机" in c_name or "headphone" in c_name:
        p_min, p_max = 40.0, 4000.0
    elif "手环" in c_name or "手表" in c_name or "watch" in c_name or "band" in c_name or "wearable" in c_name:
        p_min, p_max = 70.0, 6000.0
    else:
        p_min, p_max = 40.0, 8000.0

    valid_prices = [p for p in extracted_prices if p_min <= p <= p_max]
    if not valid_prices:
        logger.info(f"[PriceCalibration] No valid prices extracted in range ({p_min}-{p_max})")
        return None, None

    valid_prices.sort()
    calibrated_price = Decimal(str(valid_prices[len(valid_prices) // 2])).quantize(Decimal("0.01"))
    
    # 默认按60%的成本系数倒推
    cost_price = (calibrated_price * Decimal("0.60")).quantize(Decimal("0.01"))
    logger.info(f"[PriceCalibration] Calibrated Price for '{brand_name} {product_line}': ¥{calibrated_price} (Cost: ¥{cost_price})")
    return calibrated_price, cost_price


def _generate_real_world_event_via_search(day: int):
    """
    联网搜索最新科技与数码电子市场资讯，利用 LLM 生成当前的真实市场事件。
    """
    logger.info(f"[MarketAgent] Generating real world event via web search...")
    query = "consumer electronics market tech hardware news trends 2026"
    search_context = _search_web(query)
    
    system_prompt = """你是一个数码电子产品与科技硬件市场分析专家。请根据给定的最新市场新闻与行业趋势，提炼并设计一个当前可能发生的影响电商平台销售的“市场事件”。
必须以 JSON 格式返回，不要包含任何 Markdown 代码块外的说明性文字。

JSON格式模板：
{
  "name": "事件的精简名称 (不超过15字，如 'AIGC显卡需求激增' 或 '高通芯片短缺危机')",
  "emoji": "一个代表该事件的单字符表情符号 (如 '🔌' 或 '📈')",
  "type": "事件类型，必须是以下之一: 'demand_boost' (需求激增), 'demand_drop' (需求下滑), 'price_up' (价格上涨), 'price_down' (价格下跌), 'category_boom' (品类爆发)",
  "category": "主要影响的产品品类，必须是以下之一: 'laptop', 'phone', 'headphone', 'monitor', 'gaming', 'all'",
  "impact": 影响幅度的浮点数百分比 (范围在 10.0 到 80.0 之间，若属于下滑/下跌则必须为负数，如 25.5 代表需求或价格上涨25.5%，-15.0 代表下滑15%)",
  "duration": 持续天数 (整数，在 3 到 7 之间),
  "desc": "对该市场事件的详细背景描述 (80字以内，需体现出2026年的市场现实背景)"
}"""

    user_message = f"""当前模拟天数：Day {day}
联网检索到的行业新闻数据：
{search_context if search_context else '（未搜索到行业新闻，请利用您脑海中的合理科技产品知识进行发散生成）'}

请依据上述行业背景设计一个合理的市场事件并返回JSON："""

    try:
        text = _call_agnes_api(system_prompt, user_message)
        text = text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        evt_data = json.loads(text)
        
        event_name = evt_data.get("name", "科技趋势浪潮")
        emoji = evt_data.get("emoji", "📢")
        event_type = evt_data.get("type", "demand_boost")
        category = evt_data.get("category", "all")
        impact = float(evt_data.get("impact", 20.0))
        duration = int(evt_data.get("duration", 4))
        desc = evt_data.get("desc", "科技产业最新动态，影响了市场需求变化。")
        
        if event_type not in ["demand_boost", "demand_drop", "price_up", "price_down", "category_boom"]:
            event_type = "demand_boost"
        if category not in ["laptop", "phone", "headphone", "monitor", "gaming", "all"]:
            category = "all"
            
        event = MarketEvent.objects.create(
            event_name=event_name,
            emoji=emoji,
            event_type=event_type,
            impact_category=category,
            impact_value=impact,
            duration=duration,
            day_triggered=day,
            is_active=True,
            description=desc,
        )
        logger.info(f"[MarketAgent] Day{day} 联网事件生成并激活: {event.event_name} (类型: {event_type}, 影响: {impact}%, 持续: {duration}天)")
        return event
    except Exception as e:
        logger.warning(f"[MarketAgent] 联网生成市场事件失败: {e}")
        return None


# ══════════════════════════════════════════════════════
#  Agent 1：市场 Agent — 生成市场事件
# ══════════════════════════════════════════════════════

# 预定义事件库
EVENT_LIBRARY = [
    {
        "name": "开学季", "emoji": "🎒",
        "type": "demand_boost", "category": "laptop",
        "impact": 50.0, "duration": 5,
        "desc": "开学季来临，学生对笔记本电脑需求激增！"
    },
    {
        "name": "双十一购物节", "emoji": "🛒",
        "type": "demand_boost", "category": "all",
        "impact": 80.0, "duration": 3,
        "desc": "双十一大促！全品类需求暴涨，消费者疯狂购物。"
    },
    {
        "name": "电竞赛事季", "emoji": "🎮",
        "type": "category_boom", "category": "gaming",
        "impact": 40.0, "duration": 4,
        "desc": "国际电竞赛事引爆关注，游戏外设销量飙升。"
    },
    {
        "name": "芯片短缺危机", "emoji": "⚠️",
        "type": "price_up", "category": "laptop",
        "impact": 20.0, "duration": 7,
        "desc": "全球芯片短缺，笔记本电脑价格上涨。"
    },
    {
        "name": "旗舰新品发布", "emoji": "📱",
        "type": "demand_boost", "category": "phone",
        "impact": 35.0, "duration": 3,
        "desc": "顶级旗舰手机发布，消费者购机热情高涨。"
    },
    {
        "name": "年终促销", "emoji": "🎁",
        "type": "demand_boost", "category": "all",
        "impact": 45.0, "duration": 4,
        "desc": "年终大促，全品类折扣优惠，消费者抢购。"
    },
    {
        "name": "居家办公潮", "emoji": "🏠",
        "type": "category_boom", "category": "monitor",
        "impact": 30.0, "duration": 5,
        "desc": "居家办公需求上升，显示器和外设销量走高。"
    },
    {
        "name": "市场调整期", "emoji": "📉",
        "type": "demand_drop", "category": "all",
        "impact": -15.0, "duration": 3,
        "desc": "消费者趋于理性，整体购买欲望有所下降。"
    },
    {
        "name": "音乐节热潮", "emoji": "🎵",
        "type": "category_boom", "category": "headphone",
        "impact": 25.0, "duration": 3,
        "desc": "音乐节举办，消费者对耳机需求大增。"
    },
    {
        "name": "5G换机潮", "emoji": "📶",
        "type": "demand_boost", "category": "phone",
        "impact": 40.0, "duration": 6,
        "desc": "5G网络普及加速，用户纷纷换购新手机。"
    },
]


def simulate_market_agent(day: int) -> list:
    """
    市场Agent：根据概率随机触发市场事件
    返回：本次触发的事件列表
    """
    triggered = []

    # 结束已过期事件
    expired = MarketEvent.objects.filter(
        is_active=True,
        day_triggered__lt=day - 0
    )
    for evt in expired:
        if day >= evt.day_triggered + evt.duration:
            evt.is_active = False
            evt.save(update_fields=["is_active"])

    # 随机触发新事件：如果是5的倍数天，触发概率50%，否则30%
    trigger_chance = 0.5 if day % 5 == 0 else 0.30

    if random.random() < trigger_chance:
        # 有 50% 概率触发联网的真实科技事件
        if random.random() < 0.50:
            event = _generate_real_world_event_via_search(day)
            if event:
                triggered.append(event)
                return triggered

        # 否则回退到预定义的 EVENT_LIBRARY
        active_names = set(
            MarketEvent.objects.filter(is_active=True).values_list("event_name", flat=True)
        )
        available = [e for e in EVENT_LIBRARY if e["name"] not in active_names]
        if available:
            evt_data = random.choice(available)
            event = MarketEvent.objects.create(
                event_name=evt_data["name"],
                emoji=evt_data["emoji"],
                event_type=evt_data["type"],
                impact_category=evt_data["category"],
                impact_value=evt_data["impact"],
                duration=evt_data["duration"],
                day_triggered=day,
                is_active=True,
                description=evt_data["desc"],
            )
            triggered.append(event)
            logger.info(f"[MarketAgent] Day{day} 触发事件: {event.event_name}")

    return triggered


def simulate_brand_agents(day: int) -> list:
    """
    品牌Agent：根据销售状况、库存、流动资金和市场事件做出决策
    支持存货淘汰优胜劣汰、R&D 竞争力升级、破产状态判断等机制
    """
    brands = BrandAgent.objects.all()
    logs = []

    for brand in brands:
        # 1. 破产状态判断
        if brand.funds <= 0 and not brand.is_bankrupt:
            brand.is_bankrupt = True
            brand.save(update_fields=["is_bankrupt"])
            
        if brand.is_bankrupt:
            action_type = "steady"
            description = f"{brand.brand_name} 资金链断裂宣告破产，退出市场竞争，暂停所有运营活动。"
            log = BrandActionLog.objects.create(
                brand=brand,
                day=day,
                action_type=action_type,
                description=description,
                price_change_pct=0.0,
                sales_impact=0
            )
            logs.append(log)
            logger.info(f"[BrandAgent] Day{day} {brand.brand_name} (已破产): {action_type}")
            continue

        # ── 通过 FK 查询品牌商品 ──
        all_brand_products = Product.objects.filter(brand=brand)
        active_products = all_brand_products.filter(is_active=True)
        inactive_products = all_brand_products.filter(is_active=False)
        total_stock = sum(p.Stock for p in active_products)
        active_count = active_products.count()

        # 该品牌近期订单量
        recent_order_items = OrderItem.objects.filter(
            Product__brand=brand
        ).count()

        # 计算存货压力 (库存积压高 & 销售量低于目标)
        inventory_pressure = (total_stock > 60) and (recent_order_items < brand.target_sales)

        action_type = "steady"
        description = f"{brand.brand_name} 维持当前策略，市场稳步运营。"
        price_change = 0.0
        sales_impact = 0

        # ═══ 主策略决策 ═══
        if brand.strategy == "premium":
            if total_stock > 50 and active_count > 0:
                action_type = "price_cut"
                price_change = -3.0
                sales_impact = random.randint(2, 8)
                description = f"{brand.brand_name} 感知库存积压，小幅降价{abs(price_change)}%以刺激销量。"
                _apply_price_change(active_products, price_change)
            else:
                # 广告投放花费5,000元流动资金
                if random.random() > 0.5 and brand.funds >= 5000:
                    action_type = "ad_campaign"
                    brand.funds -= Decimal("5000.00")
                    description = f"{brand.brand_name} 维持高端品牌定位，投入5,000元进行品牌推广宣传。"
                    brand.reputation = _clamp(brand.reputation + random.uniform(0.5, 1.5), 0, 100)
                else:
                    action_type = "steady"

        elif brand.strategy == "aggressive":
            # 闪购活动花费3,000元促销推广费
            if random.random() < brand.aggressiveness and brand.funds >= 3000:
                action_type = "flash_sale"
                brand.funds -= Decimal("3000.00")
                price_change = -random.uniform(5, 12)
                sales_impact = random.randint(5, 20)
                description = f"{brand.brand_name} 投入3,000元促销费发起限时闪购，降价{abs(price_change):.1f}%，冲击市场份额！"
                _apply_price_change(active_products, price_change)
                relaunched = _relaunch_products(inactive_products)
                if relaunched > 0:
                    description += f" 同时重新上架{relaunched}件商品。"
            else:
                # 广告投放花费5,000元
                if brand.funds >= 5000:
                    action_type = "ad_campaign"
                    brand.funds -= Decimal("5000.00")
                    sales_impact = random.randint(3, 10)
                    description = f"{brand.brand_name} 投入5,000元进行大手笔广告投放，提升品牌曝光度。"
                    brand.reputation = _clamp(brand.reputation + random.uniform(1, 3), 0, 100)
                else:
                    action_type = "steady"

        elif brand.strategy == "branding":
            if random.random() < 0.4 and brand.funds >= 5000:
                action_type = "ad_campaign"
                brand.funds -= Decimal("5000.00")
                description = f"{brand.brand_name} 投入5,000元进行品牌投放，强化市场认知度。"
                brand.reputation = _clamp(brand.reputation + random.uniform(1, 4), 0, 100)
                sales_impact = random.randint(2, 8)
            elif recent_order_items < brand.target_sales // 2:
                action_type = "price_cut"
                price_change = -5.0
                description = f"{brand.brand_name} 销量低于目标，适当降价刺激市场。"
                _apply_price_change(active_products, price_change)
                sales_impact = random.randint(3, 12)

        elif brand.strategy == "stable":
            if total_stock > 80 and active_count > 0:
                action_type = "price_cut"
                price_change = -5.0
                sales_impact = random.randint(2, 6)
                description = f"{brand.brand_name} 库存积压超过阈值，执行降价5%清库存。"
                _apply_price_change(active_products, price_change)
            elif recent_order_items > brand.target_sales * 1.5:
                action_type = "price_hike"
                price_change = 3.0
                description = f"{brand.brand_name} 销量爆发，适度提价{price_change}%维持利润。"
                _apply_price_change(active_products, price_change)
                sales_impact = -random.randint(1, 4)

        # ═══ 存货淘汰与优胜劣汰 ═══
        # 1) 如果面临存货压力，且在售商品大于等于4个，淘汰下架综合竞争力最低的旧产品
        obsoleted_msg = ""
        if inventory_pressure and active_count >= 4:
            lowest_p = active_products.order_by("PerformanceScore", "DesignScore").first()
            if lowest_p:
                lowest_p.is_active = False
                lowest_p.save(update_fields=["is_active"])
                obsoleted_msg = f" 同时因面临存货压力，下架淘汰了低竞争力旧产品「{lowest_p.ProductName}」(综合竞争力 {lowest_p.competitiveness_score}%)。"
                description += obsoleted_msg
                active_count -= 1

        # ═══ 商品生命周期管理 & 补货（需要资金） ═══
        # 2) 自动进货补仓 (需要流动资金扣减)
        restocked = _auto_restock(active_products, brand)
        if restocked > 0 and action_type == "steady" and obsoleted_msg == "":
            action_type = "restock"
            description = f"{brand.brand_name} 检测到{restocked}件商品库存不足，消耗资金执行自动补货。"
            sales_impact = random.randint(2, 8)

        # 3) 滞销商品下架（库存高 + 无销量，但至少保留1件在售）
        if active_count > 1 and total_stock > 60 and recent_order_items == 0 and random.random() < 0.3 and obsoleted_msg == "":
            delisted = _delist_slow_products(active_products)
            if delisted > 0 and action_type == "steady":
                action_type = "delist"
                description = f"{brand.brand_name} 决定下架{delisted}件滞销商品以优化库存。"
                sales_impact = -random.randint(1, 3)

        # 4) 重新上架
        if brand.reputation > 85 and inactive_products.exists() and random.random() < 0.4 and obsoleted_msg == "":
            relaunched = _relaunch_products(inactive_products)
            if relaunched > 0 and action_type == "steady":
                action_type = "launch"
                description = f"{brand.brand_name} 品牌声誉良好，重新上架{relaunched}件商品拓展产品线。"
                sales_impact = random.randint(3, 10)

        # ═══ 优胜劣汰 R&D 新品研发机制 ═══
        # 5) 如果面临存货压力或在售品类过少，且流动资金充裕(>=25000元)，投入20000元研发资金发布高竞争力新品(得分+8)
        if (inventory_pressure or active_count < 3) and brand.funds >= 25000 and active_count < 6 and random.random() < 0.3:
            brand.funds -= Decimal("20000.00")
            new_product = _generate_product_with_ai(brand, day, boost_competitiveness=True)
            if new_product:
                action_type = "new_product"
                description = f"{brand.brand_name} 投入20,000元研发基金，成功研发上架了极具竞争力的新一代产品「{new_product.ProductName}」(竞争力 {new_product.competitiveness_score}%)，定价¥{new_product.Price}！"
                sales_impact = random.randint(8, 22)
                if obsoleted_msg:
                    description += f"（此前已下架淘汰了竞争力低的旧型号）"
        # 普通发布 (Day20%概率，需要 10,000元生产首批资金，无竞争力加成)
        elif brand.reputation > 75 and active_count < 6 and brand.funds >= 10000 and random.random() < 0.2 and action_type == "steady":
            brand.funds -= Decimal("10000.00")
            new_product = _generate_product_with_ai(brand, day, boost_competitiveness=False)
            if new_product:
                action_type = "new_product"
                description = f"{brand.brand_name} 投入10,000元首发资金发布AI新品「{new_product.ProductName}」，定价¥{new_product.Price}，已自动上架！"
                sales_impact = random.randint(5, 15)

        brand.save()

        log = BrandActionLog.objects.create(
            brand=brand,
            day=day,
            action_type=action_type,
            description=description,
            price_change_pct=price_change,
            sales_impact=sales_impact,
        )
        logs.append(log)
        logger.info(f"[BrandAgent] Day{day} {brand.brand_name}: {action_type} | Funds: {brand.funds}")

    return logs


def _apply_price_change(products, pct: float):
    """对商品列表批量调整价格"""
    for product in products:
        new_price = product.Price * Decimal(str(1 + pct / 100))
        product.Price = max(Decimal("1.00"), new_price.quantize(Decimal("0.01")))
        product.save(update_fields=["Price"])


def _auto_restock(products, brand) -> int:
    """自动补货：库存为0的商品补入随机数量，并消耗流动资金"""
    if brand.is_bankrupt:
        return 0  # 破产的品牌无法进货补仓

    count = 0
    for p in products:
        if p.Stock <= 0:
            restock_qty = random.randint(10, 50)
            cost_price = p.CostPrice if p.CostPrice > 0 else (p.Price * Decimal("0.60"))
            total_cost = cost_price * restock_qty
            
            if brand.funds >= total_cost:
                brand.funds -= total_cost
                p.Stock = restock_qty
                p.save(update_fields=["Stock"])
                count += 1
            else:
                possible_qty = int(brand.funds / cost_price)
                if possible_qty > 0:
                    brand.funds -= cost_price * possible_qty
                    p.Stock = possible_qty
                    p.save(update_fields=["Stock"])
                    count += 1
                    
    brand.save(update_fields=["funds"])
    return count


def _delist_slow_products(active_products) -> int:
    """下架滞销商品（库存最高的1件），但至少保留1件在售"""
    if active_products.count() <= 1:
        return 0
    worst = active_products.order_by("-Stock").first()
    if worst:
        worst.is_active = False
        worst.save(update_fields=["is_active"])
        return 1
    return 0


def _relaunch_products(inactive_products) -> int:
    """重新上架已下架的商品"""
    count = 0
    for p in inactive_products:
        p.is_active = True
        if p.Stock <= 0:
            p.Stock = random.randint(10, 30)
        p.save(update_fields=["is_active", "Stock"])
        count += 1
    return count


# ══════════════════════════════════════════════════════
#  品牌Agent — AI新品发布系统
# ══════════════════════════════════════════════════════

# 每个品牌的产品线模板（用于引导LLM生成合理的新品）
NEW_PRODUCT_TEMPLATES = {
    "Apple": {
        "product_lines": ["iPhone", "MacBook", "iPad", "AirPods", "Apple Watch", "Mac Studio", "Apple Vision"],
        "style": "minimalist, premium aluminum design, Apple aesthetic",
        "price_range": (2999, 12999),
        "category_map": {"iPhone": 1, "MacBook": 2, "iPad": 2, "AirPods": 3, "Apple Watch": 4, "Mac Studio": 2, "Apple Vision": 4},
    },
    "Xiaomi": {
        "product_lines": ["Xiaomi", "Redmi", "POCO", "Xiaomi Pad", "Xiaomi Buds", "Xiaomi Band", "Xiaomi Router"],
        "style": "modern tech, sleek design, vibrant colors, Xiaomi branding",
        "price_range": (499, 5999),
        "category_map": {"Xiaomi": 1, "Redmi": 1, "POCO": 1, "Xiaomi Pad": 2, "Xiaomi Buds": 3, "Xiaomi Band": 4, "Xiaomi Router": 4},
    },
    "Huawei": {
        "product_lines": ["Huawei Mate", "Huawei P", "Huawei nova", "MatePad", "FreeBuds", "Huawei Watch", "MateBook"],
        "style": "elegant, professional, Huawei design language, warm tones",
        "price_range": (1999, 8999),
        "category_map": {"Huawei Mate": 1, "Huawei P": 1, "Huawei nova": 1, "MatePad": 2, "FreeBuds": 3, "Huawei Watch": 4, "MateBook": 2},
    },
    "Lenovo": {
        "product_lines": ["ThinkPad", "IdeaPad", "Legion", "Yoga", "ThinkBook", "Lenovo Tab"],
        "style": "professional business design, ThinkPad black, clean lines",
        "price_range": (3499, 11999),
        "category_map": {"ThinkPad": 2, "IdeaPad": 2, "Legion": 2, "Yoga": 2, "ThinkBook": 2, "Lenovo Tab": 2},
    },
}


def _generate_product_with_ai(brand, day: int, boost_competitiveness: bool = False):
    """
    AI新品发布：调用LLM生成商品名+描述+参数+评分，调用Agnes Image生成宣传图
    支持根据研发投入 boost_competitiveness 提升产品竞争力分数
    返回：创建的Product对象，失败返回None
    """
    template = NEW_PRODUCT_TEMPLATES.get(brand.brand_name)
    if not template:
        return None

    product_line = random.choice(template["product_lines"])
    category_id = template["category_map"].get(product_line, 1)

    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        category = Category.objects.first()

    # ── Step 1: 调用LLM生成商品名称、描述、规格及得分 ──
    product_info = _generate_product_info_with_llm(brand.brand_name, product_line, category.CategoryName)
    if not product_info:
        return None

    product_name = product_info.get("name", f"{product_line} AI Edition")
    product_desc = product_info.get("description", f"{brand.brand_name}最新AI生成产品，品质卓越。")
    specs = product_info.get("specs", {})
    
    boost_val = 8 if boost_competitiveness else 0
    perf_score = min(100, int(product_info.get("performance_score", 80)) + boost_val)
    dsgn_score = min(100, int(product_info.get("design_score", 80)) + boost_val)
    util_score = min(100, int(product_info.get("utility_score", 80)) + boost_val)

    # 检查是否重名
    if Product.objects.filter(ProductName=product_name).exists():
        product_name = f"{product_name} ({day}代)"

    # 尝试联网进行价格与成本校准
    calibrated_price, calibrated_cost = _calibrate_price_via_search(brand.brand_name, product_line, category.CategoryName)
    
    if calibrated_price and calibrated_cost:
        price = calibrated_price
        # 逆向确定成本，使溢价满足各品牌经营策略
        if brand.strategy == "premium":
            cost_price = (price / Decimal(str(random.uniform(1.5, 1.85)))).quantize(Decimal("0.01"))
        elif brand.strategy == "aggressive":
            cost_price = (price / Decimal(str(random.uniform(1.1, 1.25)))).quantize(Decimal("0.01"))
        else:
            cost_price = (price / Decimal(str(random.uniform(1.3, 1.55)))).quantize(Decimal("0.01"))
    else:
        # 联网校准失败，回退到原有的规则推导
        if "手机" in category.CategoryName:
            base_min, base_max = 1200, 4500
        elif "电脑" in category.CategoryName:
            base_min, base_max = 2800, 9000
        elif "耳机" in category.CategoryName:
            base_min, base_max = 180, 1500
        else:
            base_min, base_max = 100, 2000

        avg_score = (perf_score + dsgn_score + util_score) / 3.0
        score_factor = max(0.0, min(1.0, (avg_score - 60) / 40.0))
        cost_price = Decimal(str(base_min + (base_max - base_min) * score_factor))

        # 结合品牌设定的价格范围，对成本做一次约束
        price_min, price_max = template["price_range"]
        cost_min = int(price_min * 0.45)
        cost_max = int(price_max * 0.70)
        cost_price = Decimal(str(max(cost_min, min(cost_max, int(cost_price))))).quantize(Decimal("0.01"))

        # 定价策略
        if brand.strategy == "premium":
            price = (cost_price * Decimal(str(random.uniform(1.5, 1.95)))).quantize(Decimal("0.01"))
        elif brand.strategy == "aggressive":
            price = (cost_price * Decimal(str(random.uniform(1.1, 1.25)))).quantize(Decimal("0.01"))
        else:
            price = (cost_price * Decimal(str(random.uniform(1.3, 1.55)))).quantize(Decimal("0.01"))

    # ── Step 2: 调用Agnes Image生成商品宣传图 ──
    image_prompt = (
        f"A professional product photography of {product_name}, "
        f"{template['style']}, "
        f"studio lighting, white clean background, soft shadows, "
        f"high detail, commercial product shot, 8k quality"
    )
    image_file = _call_agnes_image_api(image_prompt, product_name, day)

    # ── Step 3: 创建商品 ──
    product = Product(
        ProductName=product_name,
        Category=category,
        Price=price,
        Stock=random.randint(20, 80),
        Description=product_desc,
        brand=brand,
        is_active=True,
        Specs=specs,
        PerformanceScore=perf_score,
        DesignScore=dsgn_score,
        UtilityScore=util_score,
        CostPrice=cost_price,
    )

    if image_file:
        product.Image.save(image_file["filename"], image_file["content"], save=False)

    product.save()
    logger.info(f"[BrandAgent] AI新品发布: {product_name} (¥{price}) by {brand.brand_name}")
    return product


def _generate_product_info_with_llm(brand_name: str, product_line: str, category_name: str) -> dict:
    """
    调用Agnes LLM生成商品名称、描述、规格参数和核心竞争力评分
    返回: {"name": "...", "description": "...", "specs": {...}, "performance_score": int, "design_score": int, "utility_score": int}
    """
    system_prompt = f"""你是一个数码产品与AI电商专家。请根据给定的品牌、产品线和分类，设计一款全新数码产品，生成其产品名称、商品描述、4-5个核心规格参数以及三大核心竞争力维度评分（性能、外观设计、实用性）。
必须严格按照JSON格式返回，不要有任何 Markdown 代码块包裹以外的解释性文字。

JSON格式模板：
{{
  "name": "产品全名（包含产品线前缀，如 '{product_line} Air 3'）",
  "description": "50字以内的专业商品宣传语，突出技术卖点",
  "specs": {{
    "参数名1": "参数值1",
    "参数名2": "参数值2",
    "参数名3": "参数值3",
    "参数名4": "参数值4"
  }},
  "performance_score": 60到100之间的整数,
  "design_score": 60到100之间的整数,
  "utility_score": 60到100之间的整数
}}

要求：
1. 规格参数（specs）的键值对必须与分类「{category_name}」高度相关、专业且真实合理。
   - 例如手机类参数应包含：处理器(芯片)、运行内存(RAM)、机身存储、屏幕规格、电池与快充。
   - 电脑类参数应包含：处理器、显卡、内存、硬盘、屏幕规格。
   - 耳机类参数应包含：发声单元、降噪深度、续航时间、连接协议。
   - 智能穿戴或配件类参数应包含：屏幕/传感器、电池与续航、核心功能等。
2. 三大评分（0-100）需根据该产品线与该品牌的定位合理给出（例如 Apple 通常性能和设计偏高，Xiaomi 实用性与性价比偏高）。"""

    # ── 联网获取真实的硬件参数与最新信息 ──
    search_query = f"{brand_name} {product_line} core specs hardware specifications"
    search_context = _search_web(search_query)

    user_message = f"""品牌：{brand_name}
产品线：{product_line}
分类：{category_name}
要求：
- 名称应包含产品线前缀
- 名称要有型号感（如数字、Pro/Ultra/Max/Air等后缀）
- 描述要专业，突出技术亮点
- 必须是2026年的新款产品

以下是从网络搜索到的关于该产品最新核心参数的参考数据：
{search_context if search_context else '（未搜索到网络信息，请使用合理知识进行生成）'}

请参考上述真实硬件参数生成 specs 并给出合理的性能、外观、实用性得分。"""

    try:
        text = _call_agnes_api(system_prompt, user_message)
        text = text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        return json.loads(text)
    except Exception as e:
        logger.warning(f"[BrandAgent] LLM生成商品信息失败: {e}")
        # 兜底：根据品牌与模板生成 specs & scores
        suffix = random.choice(["Pro", "Ultra", "Max", "Air", "SE", "Plus", "Neo"])
        version = random.choice(["2026", "Gen 3", "V2", "Mark IV", "X"])
        name = f"{product_line} {suffix} {version}"
        desc = f"{brand_name}全新推出的{product_line}系列产品，搭载最新技术，性能卓越，体验非凡。"
        
        if "手机" in category_name or "phone" in category_name.lower():
            specs = {"CPU": "骁龙 8 Gen 5" if brand_name != "Apple" else "A19 Pro", "RAM": "16GB", "Storage": "512GB", "Screen": "6.7英寸 OLED 120Hz", "Battery": "5000mAh + 100W 快充"}
            p, d, u = random.randint(85, 96), random.randint(84, 95), random.randint(75, 88)
        elif "电脑" in category_name or "computer" in category_name.lower() or "laptop" in category_name.lower():
            specs = {"处理器": "Intel Core Ultra 9" if brand_name != "Apple" else "Apple M5", "显卡": "RTX 4060 独显" if brand_name != "Apple" else "Apple 10核GPU", "内存": "32GB LPDDR5x", "硬盘": "1TB SSD", "屏幕": "14英寸 OLED (120Hz)"}
            p, d, u = random.randint(85, 98), random.randint(85, 96), random.randint(70, 85)
        elif "耳机" in category_name or "headphone" in category_name.lower():
            specs = {"功能": "智能主动降噪 (48dB ANC)", "续航时间": "单次充电可使用 7 小时 / 搭配充电盒 35 小时", "连接协议": "蓝牙 5.4", "声学结构": "11mm 动圈 + 特制平板双单元"}
            p, d, u = random.randint(80, 92), random.randint(82, 94), random.randint(80, 92)
        else:
            specs = {"屏幕规格": "1.43英寸 AMOLED 触控屏", "续航性能": "典型使用可达 10 天", "传感器": "高精度生物体征感应器 (心率/血氧/压力)", "核心系统": "智能 HyperOS 穿戴版" if brand_name == "Xiaomi" else "HarmonyOS 智能版"}
            p, d, u = random.randint(78, 90), random.randint(80, 92), random.randint(82, 94)
            
        return {
            "name": name,
            "description": desc,
            "specs": specs,
            "performance_score": p,
            "design_score": d,
            "utility_score": u
        }


def _call_agnes_image_api(prompt: str, product_name: str, day: int) -> dict:
    """
    调用Agnes Image 2.1 Flash生成商品宣传图
    返回: {"filename": "xxx.jpg", "content": ContentFile} 或 None
    """
    api_key = getattr(settings, "AGNES_API_KEY", "")
    api_base = getattr(settings, "AGNES_API_BASE", "https://apihub.agnes-ai.com/v1")
    image_model = getattr(settings, "AGNES_IMAGE_MODEL", "agnes-image-2.1-flash")

    if not api_key:
        logger.warning("[ImageAgent] 未配置API Key，跳过图片生成")
        return None

    url = f"{api_base}/images/generations"
    payload = {
        "model": image_model,
        "prompt": prompt,
        "size": "1024x768",
        "extra_body": {
            "response_format": "b64_json"
        }
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            b64_data = result["data"][0].get("b64_json")
            if not b64_data:
                logger.warning("[ImageAgent] API返回无base64数据")
                return None

            image_bytes = base64.b64decode(b64_data)
            safe_name = product_name.replace(" ", "_").replace("/", "_")[:40]
            filename = f"ai_{safe_name}_day{day}.jpg"

            logger.info(f"[ImageAgent] 生成商品图: {filename} ({len(image_bytes)} bytes)")
            return {
                "filename": filename,
                "content": ContentFile(image_bytes),
            }

    except Exception as e:
        logger.error(f"[ImageAgent] Agnes Image API调用失败: {e}")
        return None


# ══════════════════════════════════════════════════════
#  Agent 3：顾客 Agent — 模拟购买行为
# ══════════════════════════════════════════════════════

# 偏好→商品关键词映射
PREFERENCE_KEYWORDS = {
    "gaming": ["游戏", "电竞", "Gaming", "ROG", "Razer"],
    "office": ["商务", "办公", "ThinkPad", "ProBook"],
    "high_end": ["旗舰", "Pro", "Ultra", "顶配"],
    "budget": ["性价比", "入门", "经济"],
    "student": ["学生", "轻薄", "便携"],
}

CATEGORY_KEYWORDS = {
    "laptop": ["笔记本", "电脑", "本"],
    "phone": ["手机", "Phone", "iPhone"],
    "headphone": ["耳机", "降噪"],
    "monitor": ["显示器", "屏"],
    "gaming": ["游戏", "电竞"],
    "all": [],
}


def simulate_customer_agents(day: int) -> dict:
    """
    顾客Agent：模拟每位顾客的购买决策
    返回：统计数据字典
    """
    from Simulation.models import BrandDailyStatistic
    
    customers = CustomerAgent.objects.all()
    total_sales = Decimal("0.00")
    total_profit = Decimal("0.00")
    order_count = 0
    active_customers = 0

    # 初始化每日品牌业绩累计字典
    brand_daily_data = {}
    for brand in BrandAgent.objects.all():
        brand_daily_data[brand.id] = {
            "sales_amount": Decimal("0.00"),
            "profit_amount": Decimal("0.00"),
            "order_count": 0,
        }

    # 获取当前活跃事件（影响需求）
    active_events = list(MarketEvent.objects.filter(is_active=True))

    for customer in customers:
        # 根据活跃度决定今天是否购物
        activity_boost = _get_event_activity_boost(active_events, customer.preference)
        effective_activity = _clamp(customer.activity + activity_boost, 0, 1)

        if random.random() > effective_activity:
            continue  # 今日不购物

        active_customers += 1

        # 每个顾客随机购买1-3件商品
        purchase_count = random.randint(1, 3)
        customer_spent = Decimal("0.00")

        for _ in range(purchase_count):
            product = _find_suitable_product(customer, active_events)
            if not product:
                continue

            # 计算购买数量
            qty = random.randint(1, 2)

            # 检查预算
            item_cost = product.Price * qty
            if item_cost > customer.budget - customer_spent:
                continue

            # 检查库存
            if product.Stock < qty:
                qty = product.Stock
            if qty <= 0:
                continue

            # 生成订单（归入模拟订单）
            order = Order.objects.create(
                TotalAmount=item_cost,
                PaymentMethod=random.choice(["支付宝", "微信支付", "银行卡"]),
            )
            OrderItem.objects.create(
                Order=order,
                Product=product,
                Quantity=qty,
                Price=product.Price,
            )

            # 扣减库存
            product.Stock = max(0, product.Stock - qty)
            product.save(update_fields=["Stock"])

            # 增加品牌流动资金（销售额入账，成本已在补货时扣除）
            if product.brand:
                product.brand.funds += item_cost
                product.brand.save(update_fields=["funds"])
                
                # 记录每日品牌业绩
                b_id = product.brand.id
                if b_id not in brand_daily_data:
                    brand_daily_data[b_id] = {
                        "sales_amount": Decimal("0.00"),
                        "profit_amount": Decimal("0.00"),
                        "order_count": 0
                    }
            
            # 计算利润（根据商品真实售价与成本差价核算）
            item_cost_price = product.CostPrice if product.CostPrice > 0 else (product.Price * Decimal("0.60"))
            profit = (product.Price - item_cost_price) * qty
            total_sales += item_cost
            total_profit += profit
            customer_spent += item_cost
            order_count += 1

            if product.brand:
                brand_daily_data[b_id]["sales_amount"] += item_cost
                brand_daily_data[b_id]["profit_amount"] += profit
                brand_daily_data[b_id]["order_count"] += 1

        # 更新顾客数据
        if customer_spent > 0:
            customer.total_spent += customer_spent
            customer.purchase_count += 1
            customer.save(update_fields=["total_spent", "purchase_count"])

    # 写入每个品牌的当日统计
    for b_id, data in brand_daily_data.items():
        BrandDailyStatistic.objects.update_or_create(
            brand_id=b_id,
            day=day,
            defaults={
                "sales_amount": data["sales_amount"],
                "profit_amount": data["profit_amount"],
                "order_count": data["order_count"],
            }
        )

    return {
        "total_sales": total_sales,
        "total_profit": total_profit,
        "order_count": order_count,
        "active_customers": active_customers,
    }


def _get_event_activity_boost(events: list, preference: str) -> float:
    """计算市场事件对顾客活跃度的提升"""
    boost = 0.0
    for event in events:
        if event.impact_category == "all":
            boost += event.impact_value / 200  # 全品类事件给5%~40%提升
        elif event.impact_category == preference:
            boost += event.impact_value / 150
    return _clamp(boost, 0, 0.4)


def _find_suitable_product(customer: CustomerAgent, active_events: list):
    """
    为顾客找一个合适的商品（只从上架商品中选择）
    使用基于顾客类型的多维度竞争力打分系统进行购买决策
    """
    products = Product.objects.filter(
        Price__lte=customer.budget,
        Stock__gt=0,
        is_active=True,
    )

    if not products.exists():
        return None

    candidates = list(products)

    # 顾客偏好对应的权重：(性能, 外观, 实用性, 价格敏感度)
    PREFERENCE_WEIGHTS = {
        "gaming": (0.6, 0.2, 0.2, 30.0),    # 游戏玩家：核心关注性能
        "office": (0.3, 0.2, 0.5, 30.0),    # 办公商务：关注实用性/续航
        "high_end": (0.5, 0.4, 0.1, 10.0),  # 数码发烧友：关注极致性能/外观，极低价格敏感度
        "budget": (0.2, 0.1, 0.7, 65.0),    # 性价比党：关注实用性与价格
        "student": (0.3, 0.4, 0.3, 40.0),   # 学生群体：中等敏感度，关注外观设计
    }

    w_perf, w_dsgn, w_util, price_weight = PREFERENCE_WEIGHTS.get(
        customer.preference, (0.3, 0.3, 0.4, 30.0)
    )

    scored = []
    for p in candidates:
        # 1. 规格竞争力分数 (0-100)
        spec_score = p.PerformanceScore * w_perf + p.DesignScore * w_dsgn + p.UtilityScore * w_util
        
        # 2. 价格相对于预算的性价比得分 (price_score越大，低价商品竞争力越高)
        price_ratio = float(p.Price) / float(customer.budget)
        price_score = (1.0 - price_ratio) * price_weight
        
        # 3. 品牌声誉与忠诚度加成 (0~35)
        brand_score = 0.0
        if p.brand:
            brand_score += p.brand.reputation * 0.2
            if random.random() < customer.loyalty:
                brand_score += 15.0  # 忠诚度加成
                
        # 4. 市场事件加成
        event_score = 0.0
        for event in active_events:
            cat_name = p.Category.CategoryName
            cat_matches = False
            
            if event.impact_category == "all":
                cat_matches = True
            elif event.impact_category == "phone" and "手机" in cat_name:
                cat_matches = True
            elif event.impact_category == "laptop" and "电脑" in cat_name:
                cat_matches = True
            elif event.impact_category == "headphone" and "耳" in cat_name:
                cat_matches = True
            elif event.impact_category == "gaming" and any(kw.lower() in p.ProductName.lower() for kw in ["rog", "gaming", "游戏", "电竞"]):
                cat_matches = True
            
            if cat_matches:
                event_score += event.impact_value * 0.5

        # 5. 随机扰动项
        random_score = random.uniform(-10, 10)
        
        total_score = spec_score + price_score + brand_score + event_score + random_score
        scored.append((total_score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_n = scored[:5]
    if not top_n:
        return None
    return random.choice(top_n)[1]


# ══════════════════════════════════════════════════════
#  Agent 4：AI 分析 Agent — 调用 LLM 生成经营报告
# ══════════════════════════════════════════════════════

def simulate_brand_analysis_agent(brand, day: int, brand_stats: dict) -> str:
    """
    针对单个品牌Agent生成其今日专属的AI经营分析日报，并指导其明日方向。
    """
    # 获取当前活跃事件
    active_events = list(
        MarketEvent.objects.filter(is_active=True).values_list("event_name", flat=True)
    )
    # 获取当前品牌行动日志
    brand_actions = list(
        BrandActionLog.objects.filter(brand=brand, day=day)
        .values_list("description", flat=True)
    )
    # 获取该品牌的商品销售排行（前3名）
    from django.db.models import Sum
    top_items = (
        OrderItem.objects.filter(Product__brand=brand)
        .values("Product__ProductName")
        .annotate(total_qty=Sum("Quantity"))
        .order_by("-total_qty")[:3]
    )
    top_products = [item["Product__ProductName"] for item in top_items]

    system_prompt = f"""你是一位专注于数码与电子产品领域的AI商业分析顾问。你负责为品牌「{brand.brand_name}」撰写第 {day} 天的专属经营分析日报。
请根据该品牌今日的销售表现和市场状况，进行分析并给出后续经营指导策略。
报告应包含：
1. 📈 今日业绩剖析（销售额、利润、订单量及当前流动资金）
2. ⚔️ 竞争环境与风险（市场事件的影响，竞品动作分析）
3. 🎯 下步行动指南（广告、降价促销、补货或研发新品等策略建议，需契合其主策略「{brand.get_strategy_display()}」）
请用中文输出，控制在250字以内，重点突出、语气专业且具有极强的商业决策指导性。"""

    user_message = f"""请为品牌 {brand.brand_name} 生成第 {day} 天的专属经营分析日报：

数据概况：
- 今日销售额：¥{brand_stats['sales']:.2f}
- 今日利润：¥{brand_stats['profit']:.2f}
- 今日订单量：{brand_stats['order_count']} 单
- 当前流动资金：¥{brand.funds:.2f} (是否已破产: {'是' if brand.is_bankrupt else '否'})

品牌动态：
- 今日行动：{brand_actions[0] if brand_actions else '无特殊行动，维持常规运作。'}
- 畅销商品：{', '.join(top_products) if top_products else '暂无'}

当前市场大环境事件：{', '.join(active_events) if active_events else '无特殊市场事件影响。'}

请生成分析报告："""

    report_text = _call_agnes_api(system_prompt, user_message)
    return report_text


def _generate_fallback_brand_report(brand, day: int, brand_stats: dict) -> str:
    """生成品牌分析日报的兜底文本"""
    status_str = "已破产并退出市场" if brand.is_bankrupt else "经营状态良好"
    return f"【{brand.brand_name} 品牌经营分析 - Day {day}】\n今日销售额累计达 ¥{brand_stats['sales']:.2f}，实现利润 ¥{brand_stats['profit']:.2f}，产生交易共 {brand_stats['order_count']} 笔。当前品牌流动资金为 ¥{brand.funds:.2f}，{status_str}。\n受近期市场事件影响，建议品牌密切监控库存波动，继续坚守「{brand.get_strategy_display()}」战略进行补货及营销投放。"


def _get_top_products(limit: int = 3) -> list:
    """获取热销商品名称"""
    from django.db.models import Sum
    top = (
        OrderItem.objects
        .values("Product__ProductName")
        .annotate(total_qty=Sum("Quantity"))
        .order_by("-total_qty")[:limit]
    )
    return [item["Product__ProductName"] for item in top]


def _call_agnes_api(system_prompt: str, user_message: str) -> str:
    """调用 Agnes-2.0-Flash API"""
    api_key = getattr(settings, "AGNES_API_KEY", "")
    api_base = getattr(settings, "AGNES_API_BASE", "https://apihub.agnes-ai.com/v1")
    model = getattr(settings, "AGNES_MODEL", "agnes-2.0-flash")

    if not api_key:
        return "⚠️ 未配置 Agnes API Key，无法生成AI报告。请在 settings.py 中设置 AGNES_API_KEY。"

    url = f"{api_base}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.7,
        "max_tokens": 800,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"[AnalysisAgent] Agnes API 调用失败: {e}")
        return _generate_fallback_report()


def _generate_fallback_report() -> str:
    """API不可用时的兜底报告模板"""
    return """📊 今日经营概况
受市场行情影响，今日销售整体保持稳定态势，各品牌积极参与市场竞争，促销活动带动了消费者购买热情。

🔍 原因分析
• 活跃的市场事件有效刺激了消费需求
• 品牌竞争策略动态调整，价格体系趋于合理
• 顾客Agent根据偏好精准匹配商品，转化率较高

⚠️ 风险提示
• 部分商品库存消耗速度较快，需关注补货节奏
• 价格战压力持续，注意利润率变化
• 市场热度可能出现波动，建议做好应对准备

💡 明日策略建议
1. 对库存不足的热销品类提前补货
2. 持续监控竞品价格动态，灵活调整定价
3. 借助活跃市场事件窗口期，加大推广力度"""


def _grow_customer_base(day: int):
    """
    动态顾客增长：每日推进时，有 60% 概率引入 1-2 名全新顾客
    """
    if random.random() > 0.60:
        return

    num_new = random.randint(1, 2)
    surnames = ["李", "王", "张", "刘", "陈", "杨", "赵", "黄", "周", "徐", "孙", "胡", "朱", "高", "林"]
    names = ["伟", "芳", "强", "杰", "娟", "敏", "洋", "艳", "勇", "军", "涛", "超", "明", "辉", "丽", "华", "磊", "超", "娜", "静", "宇", "鑫", "波", "浩"]
    
    occupations = ["student", "white_collar", "engineer", "freelancer", "executive"]
    preferences = ["gaming", "office", "high_end", "budget", "student"]
    
    # 职业与偏好的默认预算和活跃度映射
    pref_budgets = {
        "gaming": (4000, 12000),
        "office": (3000, 8000),
        "high_end": (8000, 25000),
        "budget": (1500, 4000),
        "student": (1000, 3000),
    }

    for _ in range(num_new):
        surname = random.choice(surnames)
        given_name = random.choice(names)
        if random.random() < 0.3:
            given_name += random.choice(names) # 双字名
        name = surname + given_name
        
        age = random.randint(18, 45)
        occupation = random.choice(occupations)
        preference = random.choice(preferences)
        
        min_b, max_b = pref_budgets[preference]
        budget = Decimal(str(round(random.uniform(min_b, max_b), 2)))
        
        loyalty = round(random.uniform(0.3, 0.8), 2)
        activity = round(random.uniform(0.4, 0.9), 2)
        
        CustomerAgent.objects.create(
            name=name,
            age=age,
            occupation=occupation,
            budget=budget,
            preference=preference,
            loyalty=loyalty,
            activity=activity,
        )
        logger.info(f"[CustomerGrowth] Day {day} - 新增顾客: {name} ({occupation}, 预算: ¥{budget}, 偏好: {preference})")


# ══════════════════════════════════════════════════════
#  主控函数：推进一天
# ══════════════════════════════════════════════════════

def advance_day() -> dict:
    """
    时间推进主控函数
    执行顺序：市场Agent → 品牌Agent → 顾客Agent → 分析Agent
    返回：当日完整统计结果
    """
    if not _advance_day_lock.acquire(blocking=False):
        raise RuntimeError("已经有一个推进日程的任务正在运行，请勿重复点击，请刷新页面检查当前天数！")
    try:
        state = SimulationState.get_instance()
        day = state.current_day

        logger.info(f"[Simulation] ====== Day {day} 开始模拟 ======")

        # Step 0: 动态顾客增长
        _grow_customer_base(day)

        # Step 1: 市场Agent
        triggered_events = simulate_market_agent(day)

        # Step 2: 品牌Agent
        brand_logs = simulate_brand_agents(day)

        # Step 3: 顾客Agent
        customer_stats = simulate_customer_agents(day)

        # Step 4: 更新品牌市场份额（根据订单量重新计算）
        _update_brand_market_share(day)

        # Step 6: 保存每日汇总统计
        stat, _ = DailyStatistic.objects.update_or_create(
            day=day,
            defaults={
                "total_sales": customer_stats["total_sales"],
                "total_profit": customer_stats["total_profit"],
                "order_count": customer_stats["order_count"],
                "customer_count": customer_stats["active_customers"],
                "active_events": len(triggered_events) + MarketEvent.objects.filter(is_active=True).count(),
            }
        )

        # Step 5 & 7: AI经营日报生成 — 为每个品牌生成专属日报
        active_event_names = ", ".join(
            MarketEvent.objects.filter(is_active=True).values_list("event_name", flat=True)
        ) or "无特殊事件"

        brands = list(BrandAgent.objects.all())
        brand_reports_summary = []
        
        for brand in brands:
            b_stat = BrandDailyStatistic.objects.filter(brand=brand, day=day).first()
            b_stats_dict = {
                "sales": float(b_stat.sales_amount) if b_stat else 0.0,
                "profit": float(b_stat.profit_amount) if b_stat else 0.0,
                "order_count": b_stat.order_count if b_stat else 0,
            }
            
            if brand.is_bankrupt:
                report_text = f"【{brand.brand_name} 破产公告 - Day {day}】\n品牌流动资金枯竭，已宣告破产，今日暂停营业，不进行任何商业活动及AI经营分析。"
                is_ai = False
            else:
                try:
                    report_text = simulate_brand_analysis_agent(brand, day, b_stats_dict)
                    is_ai = True
                except Exception as e:
                    logger.warning(f"[AnalysisAgent] Brand {brand.brand_name} report generation failed: {e}")
                    report_text = _generate_fallback_brand_report(brand, day, b_stats_dict)
                    is_ai = False
                    
            # 获取该品牌最畅销的商品
            from django.db.models import Sum
            top = (
                OrderItem.objects.filter(Product__brand=brand)
                .values("Product__ProductName")
                .annotate(total_qty=Sum("Quantity"))
                .order_by("-total_qty")
                .first()
            )
            top_product_name = top["Product__ProductName"] if top else ""
            
            DailyReport.objects.update_or_create(
                brand=brand,
                day=day,
                defaults={
                    "sales_amount": Decimal(str(b_stats_dict["sales"])),
                    "profit_amount": Decimal(str(b_stats_dict["profit"])),
                    "order_count": b_stats_dict["order_count"],
                    "top_product": top_product_name,
                    "active_events_summary": active_event_names,
                    "report_text": report_text,
                    "is_ai_generated": is_ai,
                }
            )
            
            if not brand.is_bankrupt:
                brand_reports_summary.append(f"{brand.brand_name}: {report_text[:60]}...")

        # Step 8: 推进天数
        state.current_day += 1
        state.save()

        report_preview_text = " | ".join(brand_reports_summary)
        result = {
            "day": day,
            "next_day": state.current_day,
            "total_sales": float(customer_stats["total_sales"]),
            "total_profit": float(customer_stats["total_profit"]),
            "order_count": customer_stats["order_count"],
            "active_customers": customer_stats["active_customers"],
            "triggered_events": [e.event_name for e in triggered_events],
            "brand_actions_count": len(brand_logs),
            "report_preview": report_preview_text[:120] + "..." if len(report_preview_text) > 120 else report_preview_text,
        }

        logger.info(f"[Simulation] Day {day} 完成: 销售额¥{result['total_sales']:.2f}, 订单{result['order_count']}单")
        return result
    finally:
        _advance_day_lock.release()


def _update_brand_market_share(day: int):
    """根据订单量重新计算品牌市场份额（通过 Product.brand FK 关联）"""
    from django.db.models import Sum

    brands = BrandAgent.objects.all()
    brand_sales = {}
    total_qty = 0

    for brand in brands:
        qty = OrderItem.objects.filter(
            Product__brand=brand
        ).aggregate(total=Sum("Quantity"))["total"] or 0
        brand_sales[brand.id] = qty
        total_qty += qty

    if total_qty > 0:
        for brand in brands:
            share = (brand_sales[brand.id] / total_qty) * 100
            brand.market_share = round(share, 2)
            brand.total_sales = brand_sales[brand.id]
            brand.save(update_fields=["market_share", "total_sales"])
