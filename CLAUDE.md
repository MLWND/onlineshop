# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TechMall is a Django 4.2 course project — a Chinese-language AI电商生态模拟平台。It combines a **digital electronics e-commerce storefront** with a **multi-Agent market simulation system**. Uses SQLite, server-rendered HTML templates with Bootstrap 5 (CDN), Chart.js 4, and Agnes LLM/Image APIs. Cart is global (no user/session scoping).

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations and load seed data (4 categories, 20 products)
python manage.py migrate
python manage.py loaddata Shop/fixtures/initial_data.json

# Start dev server
python manage.py runserver

# Create admin superuser
python manage.py createsuperuser

# Run Django shell
python manage.py shell

# Reset simulation data to Day 1
python scratch/reset_all_data.py

# Assign products to brand agents
python manage.py assign_brands
```

No test suite, linter, or CI is configured.

## Architecture

**Two-app project** — `TechMall/` is the Django project config, `Shop/` is the e-commerce app, `Simulation/` is the AI simulation app.

- **Models** (`Shop/models.py`): `Category`, `Product`, `Cart`, `Order`, `OrderItem`. Field names use PascalCase (e.g., `ProductName`, `Price`, `Stock`). Product has `brand` FK to `BrandAgent`, plus `is_active`, `Specs` (JSON), `PerformanceScore`, `DesignScore`, `UtilityScore`, `CostPrice`.
- **Models** (`Simulation/models.py`): `SimulationState` (singleton), `BrandAgent`, `CustomerAgent`, `MarketEvent`, `DailyStatistic`, `BrandActionLog`, `DailyReport`, `BrandDailyStatistic`. BrandAgent has `logo_url` property returning SVG path (`/static/images/logos/{brand}.svg`).
- **Views** (`Shop/views.py`): Function-based views. The cart is a single shared DB table. `_sync_order_to_simulation()` syncs real user orders to the simulation system.
- **Views** (`Simulation/views.py`): Dashboard, brands, customers, events, reports views + `_assign_products_to_brands()` auto-assignment function.
- **Agents** (`Simulation/agents.py`): Four core agents — Market Agent (events), Brand Agent (pricing/strategy/R&D), Customer Agent (purchases), Analysis Agent (AI reports via Agnes API). Main entry: `advance_day()` with `threading.Lock` for concurrency.
- **Templates** (`templates/`): All pages extend `base.html`. A global `cart_context` context processor injects `cart_count`. Templates use `brand-logo-img` class for SVG brand logos.
- **Static/Static files**: Light-theme CSS design system in `static/css/style.css`. Brand SVG logos in `static/images/logos/`. Product images in `media/products/` (source images in `image/`).
- **Fixtures**: `Shop/fixtures/initial_data.json` contains seed data for 4 categories and 20 products with image paths.
- **Scripts**: `scratch/reset_all_data.py` (full reset to Day 1), `scratch/fix_images.py` (download placeholder images). Root-level utility scripts: `replace_emojis.py` (emoji→SVG migration), `clean_svgs.py` (SVG cleanup).

## Key Patterns

- **Brand assignment**: Products are auto-assigned to BrandAgent via name keyword matching (`_assign_products_to_brands()` in views.py, also as management command `assign_brands`).
- **Brand logos**: Uses SVG files in `static/images/logos/` (apple.svg, xiaomi.svg, huawei.svg, lenovo.svg). Accessed via `BrandAgent.logo_url` property. Template pattern: `<img src="{{ ba.logo_url }}" class="brand-logo-img">`.
- **Order creation** uses `transaction.atomic()` — keep this atomic when modifying checkout.
- **Concurrency safety**: `threading.Lock` in `advance_day()` prevents duplicate simulation runs.
- **AI Integration**: Agnes API configured in `settings.py` (`AGNES_API_KEY`, `AGNES_API_BASE`, `AGNES_MODEL`, `AGNES_IMAGE_MODEL`). Used for product generation, event generation, and daily reports.
- **Web Search**: DuckDuckGo search for market events and price calibration (no API key needed).
- **CSS Design System**: Light theme with CSS variables (`--primary`, `--bg-card`, `--border`, etc.), three fonts (Outfit/Inter/JetBrains Mono), unified card system.

## URL Structure

| URL | View | Description |
|-----|------|-------------|
| `/` | `index` | Shop homepage with brand zones, categories, products |
| `/category/<id>/` | `category` | Category product listing |
| `/brand/<id>/` | `brand_zone` | Brand detail page with products and agent status |
| `/product/<id>/` | `productDetail` | Product detail with specs and competitiveness scores |
| `/cart/` | `cart` | Shopping cart |
| `/cart/add/<id>/` | `addToCart` | Add to cart |
| `/order/submit/` | `submitOrder` | Checkout (syncs to simulation) |
| `/simulation/dashboard/` | `dashboard` | Market dashboard with KPIs and charts |
| `/simulation/brands/` | `brands` | Brand competition center |
| `/simulation/customers/` | `customers` | Customer profiles |
| `/simulation/events/` | `events` | Market event timeline |
| `/simulation/reports/` | `reports` | AI daily reports center |
| `/simulation/advance/` | `advance_day` | POST: advance simulation by one day |
| `/simulation/init/` | `init_data` | Initialize seed data |

## File Structure

```
onlineshop-main/
├── TechMall/              # Django project config
├── Shop/                  # E-commerce app
│   ├── models.py          # Category, Product, Cart, Order, OrderItem
│   ├── views.py           # Shop views + cart_context + simulation sync
│   ├── management/commands/assign_brands.py
│   └── fixtures/initial_data.json
├── Simulation/            # AI simulation app
│   ├── models.py          # All simulation models
│   ├── agents.py          # Core Agent logic + advance_day()
│   └── views.py           # Dashboard/brand/customer/event/report views
├── templates/             # HTML templates (14 files)
├── static/css/style.css   # Light-theme design system
├── static/images/logos/   # Brand SVG logos
├── image/                 # Source product images (20 files)
├── media/products/        # Runtime product images
├── scratch/               # Utility scripts
│   ├── reset_all_data.py  # Full reset to Day 1
│   └── fix_images.py      # Image download fallback
├── replace_emojis.py      # Emoji→SVG migration script
├── clean_svgs.py          # SVG cleanup script
├── db.sqlite3             # SQLite database
└── manage.py              # Django management
```
