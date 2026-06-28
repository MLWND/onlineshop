"""
AI电商生态模拟平台 - 数据模型
包含：SimulationState, CustomerAgent, BrandAgent, MarketEvent,
      DailyReport, DailyStatistic, BrandActionLog
"""
from django.db import models
from django.utils import timezone


class SimulationState(models.Model):
    """全局模拟状态 - 记录当前模拟推进到第几天"""
    current_day = models.IntegerField("当前天数", default=1)
    updated_at = models.DateTimeField("最后更新", auto_now=True)

    class Meta:
        verbose_name = "模拟状态"
        verbose_name_plural = "模拟状态"

    def __str__(self):
        return f"Day {self.current_day}"

    @classmethod
    def get_instance(cls):
        """获取单例状态（始终返回第一条记录）"""
        obj, _ = cls.objects.get_or_create(id=1, defaults={"current_day": 1})
        return obj


# ──────────────────────────────────────────────
# 顾客 Agent
# ──────────────────────────────────────────────

PREFERENCE_CHOICES = [
    ("gaming", "游戏玩家"),
    ("office", "办公商务"),
    ("high_end", "数码发烧友"),
    ("budget", "性价比党"),
    ("student", "学生群体"),
]

OCCUPATION_CHOICES = [
    ("student", "学生"),
    ("white_collar", "白领"),
    ("engineer", "工程师"),
    ("freelancer", "自由职业"),
    ("executive", "管理层"),
]


class CustomerAgent(models.Model):
    """虚拟顾客 Agent"""
    name = models.CharField("顾客名称", max_length=50)
    age = models.IntegerField("年龄", default=25)
    occupation = models.CharField("职业", max_length=20, choices=OCCUPATION_CHOICES, default="student")
    budget = models.DecimalField("月度预算(元)", max_digits=10, decimal_places=2, default=5000)
    preference = models.CharField("偏好类型", max_length=20, choices=PREFERENCE_CHOICES, default="budget")
    loyalty = models.FloatField("品牌忠诚度(0-1)", default=0.5)
    activity = models.FloatField("活跃度(0-1)", default=0.7)
    total_spent = models.DecimalField("累计消费", max_digits=12, decimal_places=2, default=0)
    purchase_count = models.IntegerField("购买次数", default=0)

    class Meta:
        verbose_name = "虚拟顾客"
        verbose_name_plural = "虚拟顾客"

    def __str__(self):
        return f"{self.name}（{self.get_preference_display()}）"


# ──────────────────────────────────────────────
# 品牌 Agent
# ──────────────────────────────────────────────

BRAND_STRATEGY_CHOICES = [
    ("premium", "高端策略"),
    ("aggressive", "激进促销"),
    ("branding", "品牌优先"),
    ("stable", "稳健经营"),
]


class BrandAgent(models.Model):
    """品牌 Agent - 模拟品牌市场竞争行为"""
    brand_name = models.CharField("品牌名称", max_length=50, unique=True)
    reputation = models.FloatField("品牌声誉(0-100)", default=70.0)
    budget = models.DecimalField("营销预算(万元)", max_digits=10, decimal_places=2, default=100)
    aggressiveness = models.FloatField("激进程度(0-1)", default=0.5)
    strategy = models.CharField("经营策略", max_length=20, choices=BRAND_STRATEGY_CHOICES, default="stable")
    target_sales = models.IntegerField("目标销量(件/天)", default=10)
    total_sales = models.IntegerField("累计销量", default=0)
    total_revenue = models.DecimalField("累计营收(元)", max_digits=14, decimal_places=2, default=0)
    market_share = models.FloatField("市场份额(%)", default=25.0)
    logo_emoji = models.CharField("品牌图标", max_length=10, default="🏢")
    color = models.CharField("品牌色(hex)", max_length=10, default="#6c757d")
    funds = models.DecimalField("流动资金(元)", max_digits=14, decimal_places=2, default=100000.00)
    is_bankrupt = models.BooleanField("是否已破产", default=False)

    class Meta:
        verbose_name = "品牌Agent"
        verbose_name_plural = "品牌Agent"

    @property
    def logo_url(self):
        domains = {
            "Apple": "apple.svg",
            "Xiaomi": "xiaomi.svg",
            "Huawei": "huawei.svg",
            "Lenovo": "lenovo.svg",
        }
        filename = domains.get(self.brand_name, "apple.svg")
        return f"/static/images/logos/{filename}?v=2"

    def __str__(self):
        return self.brand_name


# ──────────────────────────────────────────────
# 市场事件
# ──────────────────────────────────────────────

EVENT_TYPE_CHOICES = [
    ("demand_boost", "需求激增"),
    ("demand_drop", "需求下滑"),
    ("price_up", "价格上涨"),
    ("price_down", "价格下跌"),
    ("category_boom", "品类爆发"),
]

CATEGORY_IMPACT_CHOICES = [
    ("all", "全品类"),
    ("laptop", "笔记本"),
    ("phone", "手机"),
    ("headphone", "耳机"),
    ("monitor", "显示器"),
    ("gaming", "游戏外设"),
]


class MarketEvent(models.Model):
    """市场事件 - 模拟外部环境变化"""
    event_name = models.CharField("事件名称", max_length=100)
    event_type = models.CharField("事件类型", max_length=20, choices=EVENT_TYPE_CHOICES)
    impact_category = models.CharField("影响品类", max_length=20, choices=CATEGORY_IMPACT_CHOICES, default="all")
    impact_value = models.FloatField("影响幅度(%)", default=20.0, help_text="正数=增长，负数=下降")
    duration = models.IntegerField("持续天数", default=3)
    day_triggered = models.IntegerField("触发天数", default=1)
    is_active = models.BooleanField("是否生效中", default=True)
    description = models.TextField("事件描述", blank=True)
    emoji = models.CharField("事件图标", max_length=10, default="📢")

    class Meta:
        verbose_name = "市场事件"
        verbose_name_plural = "市场事件"
        ordering = ["-day_triggered"]

    def __str__(self):
        return f"Day{self.day_triggered} {self.emoji}{self.event_name}"


# ──────────────────────────────────────────────
# 每日统计
# ──────────────────────────────────────────────


class DailyStatistic(models.Model):
    """每日汇总统计 - 为 Chart.js 图表提供数据"""
    day = models.IntegerField("模拟天数", unique=True)
    total_sales = models.DecimalField("当日销售额", max_digits=14, decimal_places=2, default=0)
    total_profit = models.DecimalField("当日利润", max_digits=14, decimal_places=2, default=0)
    order_count = models.IntegerField("订单数量", default=0)
    customer_count = models.IntegerField("活跃顾客数", default=0)
    active_events = models.IntegerField("活跃事件数", default=0)
    created_at = models.DateTimeField("记录时间", default=timezone.now)

    class Meta:
        verbose_name = "每日统计"
        verbose_name_plural = "每日统计"
        ordering = ["day"]

    def __str__(self):
        return f"Day{self.day} 统计"


# ──────────────────────────────────────────────
# 品牌行动日志
# ──────────────────────────────────────────────

BRAND_ACTION_CHOICES = [
    ("price_cut", "降价促销"),
    ("price_hike", "价格上调"),
    ("ad_campaign", "广告投放"),
    ("flash_sale", "限时闪购"),
    ("new_launch", "新品推广"),
    ("steady", "维持策略"),
    ("delist", "商品下架"),
    ("restock", "自动补货"),
    ("launch", "商品上架"),
    ("new_product", "AI新品发布"),
]


class BrandActionLog(models.Model):
    """品牌每日行动记录"""
    brand = models.ForeignKey(BrandAgent, verbose_name="品牌", on_delete=models.CASCADE, related_name="actions")
    day = models.IntegerField("模拟天数")
    action_type = models.CharField("行动类型", max_length=20, choices=BRAND_ACTION_CHOICES)
    description = models.TextField("行动描述")
    price_change_pct = models.FloatField("价格变动幅度(%)", default=0.0)
    sales_impact = models.IntegerField("销量影响(件)", default=0)

    class Meta:
        verbose_name = "品牌行动日志"
        verbose_name_plural = "品牌行动日志"
        ordering = ["-day"]

    def __str__(self):
        return f"Day{self.day} {self.brand.brand_name} - {self.get_action_type_display()}"


# ──────────────────────────────────────────────
# AI 日报
# ──────────────────────────────────────────────


class DailyReport(models.Model):
    """AI分析 Agent 生成的经营日报"""
    brand = models.ForeignKey(BrandAgent, verbose_name="归属品牌", on_delete=models.CASCADE, related_name="daily_reports", null=True, blank=True)
    day = models.IntegerField("模拟天数")
    sales_amount = models.DecimalField("当日销售额", max_digits=14, decimal_places=2, default=0)
    profit_amount = models.DecimalField("当日利润", max_digits=14, decimal_places=2, default=0)
    order_count = models.IntegerField("订单数", default=0)
    top_product = models.CharField("热销商品", max_length=200, blank=True)
    active_events_summary = models.TextField("市场事件摘要", blank=True)
    report_text = models.TextField("AI分析报告", blank=True)
    is_ai_generated = models.BooleanField("是否AI生成", default=False)
    created_at = models.DateTimeField("生成时间", default=timezone.now)

    class Meta:
        verbose_name = "AI经营日报"
        verbose_name_plural = "AI经营日报"
        ordering = ["-day"]
        unique_together = ("brand", "day")

    def __str__(self):
        brand_name = self.brand.brand_name if self.brand else "全局"
        return f"Day{self.day} {brand_name} AI日报"


class BrandDailyStatistic(models.Model):
    """品牌每日统计 - 记录各个品牌的今日业绩，供大屏展示和品牌Agent分析使用"""
    brand = models.ForeignKey(BrandAgent, verbose_name="归属品牌", on_delete=models.CASCADE, related_name="daily_stats")
    day = models.IntegerField("模拟天数")
    sales_amount = models.DecimalField("当日销售额", max_digits=14, decimal_places=2, default=0.00)
    profit_amount = models.DecimalField("当日利润", max_digits=14, decimal_places=2, default=0.00)
    order_count = models.IntegerField("当日订单量", default=0)
    created_at = models.DateTimeField("记录时间", default=timezone.now)

    class Meta:
        verbose_name = "品牌每日统计"
        verbose_name_plural = "品牌每日统计"
        unique_together = ("brand", "day")
        ordering = ["day", "brand"]

    def __str__(self):
        return f"Day{self.day} {self.brand.brand_name} 统计"
