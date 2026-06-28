"""Admin 后台注册 — Simulation 模块"""
from django.contrib import admin

from .models import (
    BrandActionLog,
    BrandAgent,
    CustomerAgent,
    DailyReport,
    DailyStatistic,
    MarketEvent,
    SimulationState,
)


@admin.register(SimulationState)
class SimulationStateAdmin(admin.ModelAdmin):
    list_display = ("id", "current_day", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(CustomerAgent)
class CustomerAgentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "occupation", "preference", "budget", "purchase_count", "total_spent")
    list_filter = ("occupation", "preference")
    search_fields = ("name",)


@admin.register(BrandAgent)
class BrandAgentAdmin(admin.ModelAdmin):
    list_display = ("id", "brand_name", "strategy", "reputation", "market_share", "total_sales", "total_revenue")
    list_filter = ("strategy",)
    search_fields = ("brand_name",)


@admin.register(MarketEvent)
class MarketEventAdmin(admin.ModelAdmin):
    list_display = ("id", "event_name", "event_type", "impact_category", "impact_value", "duration", "day_triggered", "is_active")
    list_filter = ("event_type", "impact_category", "is_active")
    search_fields = ("event_name",)


@admin.register(DailyStatistic)
class DailyStatisticAdmin(admin.ModelAdmin):
    list_display = ("day", "total_sales", "total_profit", "order_count", "customer_count", "active_events")
    ordering = ("-day",)


class BrandActionLogInline(admin.TabularInline):
    model = BrandActionLog
    extra = 0
    readonly_fields = ("day", "action_type", "description", "price_change_pct", "sales_impact")


@admin.register(BrandActionLog)
class BrandActionLogAdmin(admin.ModelAdmin):
    list_display = ("id", "brand", "day", "action_type", "price_change_pct", "sales_impact")
    list_filter = ("brand", "action_type")
    ordering = ("-day",)


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ("day", "sales_amount", "profit_amount", "order_count", "is_ai_generated", "created_at")
    ordering = ("-day",)
    readonly_fields = ("created_at",)
