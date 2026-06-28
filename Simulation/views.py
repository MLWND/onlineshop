"""
Simulation 视图函数
包含：dashboard, brands, customers, events, reports, advance_day_view
"""
import json
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from Shop.models import Product
from .agents import advance_day
from .models import (
    BrandActionLog,
    BrandAgent,
    CustomerAgent,
    DailyReport,
    DailyStatistic,
    MarketEvent,
    SimulationState,
)


def dashboard(request):
    """市场大屏 — 核心数据概览 + Chart.js 图表"""
    state = SimulationState.get_instance()
    current_day = state.current_day

    # KPI 数据
    stats = DailyStatistic.objects.order_by("-day")
    latest_stat = stats.first()

    total_sales = sum(s.total_sales for s in stats)
    total_profit = sum(s.total_profit for s in stats)
    total_orders = sum(s.order_count for s in stats)
    active_customers = CustomerAgent.objects.count()

    # Chart.js 数据（最近30天）
    chart_stats = list(stats.order_by("day")[:30])
    chart_days = [f"Day{s.day}" for s in chart_stats]
    chart_sales = [float(s.total_sales) for s in chart_stats]
    chart_profit = [float(s.total_profit) for s in chart_stats]
    chart_orders = [s.order_count for s in chart_stats]

    # 活跃市场事件
    active_events = MarketEvent.objects.filter(is_active=True).order_by("-day_triggered")

    # 品牌今日/昨日业绩看板数据
    brand_performances = []
    latest_reports = []
    if latest_stat:
        last_completed_day = latest_stat.day
        from .models import BrandDailyStatistic
        brands = BrandAgent.objects.all().order_by("-market_share")
        for brand in brands:
            b_stat = BrandDailyStatistic.objects.filter(brand=brand, day=last_completed_day).first()
            brand_performances.append({
                "brand": brand,
                "sales": b_stat.sales_amount if b_stat else 0.00,
                "profit": b_stat.profit_amount if b_stat else 0.00,
                "order_count": b_stat.order_count if b_stat else 0,
            })
        
        # 获取最新的分品牌AI日报
        latest_reports = list(DailyReport.objects.filter(day=last_completed_day).select_related("brand"))

    context = {
        "state": state,
        "current_day": current_day,
        "latest_stat": latest_stat,
        "total_sales": total_sales,
        "total_profit": total_profit,
        "total_orders": total_orders,
        "active_customers": active_customers,
        "active_events": active_events,
        "brand_performances": brand_performances,
        "latest_reports": latest_reports,
        # JSON for charts
        "chart_days_json": json.dumps(chart_days, ensure_ascii=False),
        "chart_sales_json": json.dumps(chart_sales),
        "chart_profit_json": json.dumps(chart_profit),
        "chart_orders_json": json.dumps(chart_orders),
    }
    return render(request, "simulation/dashboard.html", context)


def brands(request):
    """品牌中心 — 品牌竞争态势"""
    state = SimulationState.get_instance()
    brand_list = BrandAgent.objects.all().order_by("-market_share")

    # 每个品牌最近5条行动日志
    for brand in brand_list:
        brand.recent_actions = brand.actions.order_by("-day")[:5]

    # 市场份额图表数据
    brand_names = [b.brand_name for b in brand_list]
    brand_shares = [b.market_share for b in brand_list]
    brand_colors = [b.color for b in brand_list]

    context = {
        "state": state,
        "brands": brand_list,
        "brand_names_json": json.dumps(brand_names, ensure_ascii=False),
        "brand_shares_json": json.dumps(brand_shares),
        "brand_colors_json": json.dumps(brand_colors),
    }
    return render(request, "simulation/brands.html", context)


def customers(request):
    """顾客中心 — 顾客画像分析"""
    state = SimulationState.get_instance()
    customer_list = CustomerAgent.objects.all().order_by("-total_spent")

    # 偏好分布统计
    from django.db.models import Count, Sum
    preference_data = (
        CustomerAgent.objects
        .values("preference")
        .annotate(count=Count("id"), total=Sum("total_spent"))
        .order_by("-count")
    )

    pref_labels = []
    pref_counts = []
    pref_map = dict(CustomerAgent._meta.get_field("preference").choices)
    for item in preference_data:
        pref_labels.append(pref_map.get(item["preference"], item["preference"]))
        pref_counts.append(item["count"])

    # 职业分布
    occupation_data = (
        CustomerAgent.objects
        .values("occupation")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    occ_map = dict(CustomerAgent._meta.get_field("occupation").choices)
    occ_labels = [occ_map.get(d["occupation"], d["occupation"]) for d in occupation_data]
    occ_counts = [d["count"] for d in occupation_data]

    context = {
        "state": state,
        "customers": customer_list,
        "total_customers": customer_list.count(),
        "total_spent": sum(c.total_spent for c in customer_list),
        "total_purchases": sum(c.purchase_count for c in customer_list),
        "pref_labels_json": json.dumps(pref_labels, ensure_ascii=False),
        "pref_counts_json": json.dumps(pref_counts),
        "occ_labels_json": json.dumps(occ_labels, ensure_ascii=False),
        "occ_counts_json": json.dumps(occ_counts),
    }
    return render(request, "simulation/customers.html", context)


def events(request):
    """市场事件时间线"""
    state = SimulationState.get_instance()
    all_events = MarketEvent.objects.all().order_by("-day_triggered")

    context = {
        "state": state,
        "events": all_events,
        "active_events": all_events.filter(is_active=True),
        "past_events": all_events.filter(is_active=False),
    }
    return render(request, "simulation/events.html", context)


def reports(request):
    """AI经营日报中心"""
    state = SimulationState.get_instance()
    brand_id = request.GET.get("brand_id")
    
    all_reports = DailyReport.objects.all().select_related("brand").order_by("-day")
    
    if brand_id and brand_id.isdigit():
        all_reports = all_reports.filter(brand_id=int(brand_id))
        
    brands = BrandAgent.objects.all()

    context = {
        "state": state,
        "reports": all_reports,
        "latest_report": all_reports.first(),
        "total_reports": all_reports.count(),
        "brands": brands,
        "selected_brand_id": int(brand_id) if brand_id and brand_id.isdigit() else None,
    }
    return render(request, "simulation/reports.html", context)


@require_POST
def advance_day_view(request):
    """推进一天 — 触发所有 Agent 执行"""
    try:
        result = advance_day()
        messages.success(
            request,
            f"✅ Day {result['day']} 模拟完成！"
            f"销售额 ¥{result['total_sales']:.2f}，"
            f"订单 {result['order_count']} 单，"
            f"活跃顾客 {result['active_customers']} 人。"
            + (f" 触发事件：{'、'.join(result['triggered_events'])}" if result["triggered_events"] else "")
        )
    except Exception as e:
        messages.error(request, f"❌ 模拟推进失败：{e}")

    return redirect("simulation:dashboard")


def init_data_view(request):
    """初始化种子数据（仅首次使用）"""
    if SimulationState.objects.exists() or BrandAgent.objects.exists():
        messages.warning(request, "⚠️ 数据已存在，跳过初始化。如需重置请联系管理员。")
        return redirect("simulation:dashboard")

    _init_seed_data()
    messages.success(request, "🎉 初始化成功！已创建品牌Agent、顾客Agent和模拟状态。")
    return redirect("simulation:dashboard")


def _init_seed_data():
    """写入种子数据"""
    # 初始化模拟状态
    SimulationState.objects.get_or_create(id=1, defaults={"current_day": 1})

    # 品牌Agent
    brands_data = [
        {
            "brand_name": "Apple", "reputation": 95.0, "budget": 500,
            "aggressiveness": 0.2, "strategy": "premium", "target_sales": 8,
            "market_share": 30.0, "logo_emoji": "🍎", "color": "#555555",
        },
        {
            "brand_name": "Xiaomi", "reputation": 78.0, "budget": 200,
            "aggressiveness": 0.85, "strategy": "aggressive", "target_sales": 20,
            "market_share": 28.0, "logo_emoji": "📱", "color": "#FF6900",
        },
        {
            "brand_name": "Huawei", "reputation": 85.0, "budget": 350,
            "aggressiveness": 0.5, "strategy": "branding", "target_sales": 15,
            "market_share": 25.0, "logo_emoji": "🌸", "color": "#CF0A2C",
        },
        {
            "brand_name": "Lenovo", "reputation": 72.0, "budget": 180,
            "aggressiveness": 0.4, "strategy": "stable", "target_sales": 12,
            "market_share": 17.0, "logo_emoji": "💻", "color": "#E2231A",
        },
    ]
    for bd in brands_data:
        BrandAgent.objects.get_or_create(brand_name=bd["brand_name"], defaults=bd)

    # 顾客Agent
    customers_data = [
        {"name": "小明（学生）", "age": 20, "occupation": "student", "budget": 4000, "preference": "student", "loyalty": 0.4, "activity": 0.75},
        {"name": "小红（学生）", "age": 19, "occupation": "student", "budget": 3500, "preference": "budget", "loyalty": 0.3, "activity": 0.65},
        {"name": "张白领", "age": 28, "occupation": "white_collar", "budget": 10000, "preference": "office", "loyalty": 0.6, "activity": 0.7},
        {"name": "李工程师", "age": 32, "occupation": "engineer", "budget": 15000, "preference": "high_end", "loyalty": 0.5, "activity": 0.6},
        {"name": "极客王", "age": 25, "occupation": "engineer", "budget": 30000, "preference": "high_end", "loyalty": 0.7, "activity": 0.9},
        {"name": "游戏玩家赵", "age": 22, "occupation": "student", "budget": 8000, "preference": "gaming", "loyalty": 0.8, "activity": 0.85},
        {"name": "自由职业陈", "age": 30, "occupation": "freelancer", "budget": 12000, "preference": "office", "loyalty": 0.4, "activity": 0.55},
        {"name": "管理层刘总", "age": 45, "occupation": "executive", "budget": 50000, "preference": "high_end", "loyalty": 0.6, "activity": 0.4},
        {"name": "性价比党吴", "age": 26, "occupation": "white_collar", "budget": 5000, "preference": "budget", "loyalty": 0.3, "activity": 0.8},
        {"name": "音乐爱好者孙", "age": 24, "occupation": "student", "budget": 6000, "preference": "student", "loyalty": 0.5, "activity": 0.7},
    ]
    for cd in customers_data:
        CustomerAgent.objects.get_or_create(name=cd["name"], defaults=cd)

    # 自动将商品分配到对应品牌
    _assign_products_to_brands()


def _assign_products_to_brands():
    """根据商品名称关键词自动分配品牌FK"""
    BRAND_KEYWORDS = {
        "Apple": ["Apple", "iPhone", "MacBook", "AirPods", "iPad", "Apple Watch"],
        "Xiaomi": ["Xiaomi", "小米", "Redmi", "Mi "],
        "Huawei": ["Huawei", "华为", "Honor", "Mate "],
        "Lenovo": ["Lenovo", "ThinkPad", "联想"],
    }
    brands = {b.brand_name: b for b in BrandAgent.objects.all()}
    for product in Product.objects.filter(brand__isnull=True):
        for brand_name, keywords in BRAND_KEYWORDS.items():
            if brand_name not in brands:
                continue
            for kw in keywords:
                if kw.lower() in product.ProductName.lower():
                    product.brand = brands[brand_name]
                    product.save(update_fields=["brand"])
                    break
            if product.brand:
                break
