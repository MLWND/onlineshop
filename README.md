# TechMall AI 电商生态模拟系统 V3.0

> 基于 Django + Agnes LLM/Image APIs 的智能代理（Agent）电商生态对抗模拟平台 —— 深度演练、博弈与多角色经营系统。

---

## 📖 项目简介

TechMall 在传统科技数码在线商城的基础上，深度集成了一个**多 Agent 协同与博弈的 AI 模拟系统**。该系统模拟了包含**市场环境、品牌商家、消费者、商业分析师**四个核心角色的电商大生态，主要用于演练复杂市场博弈、定价校准及智能报告生成。

平台已全面实现分品牌销售大屏、品牌专属 AI 经营日报、联网真实价格校准以及联网动态科技事件等重大升级，并配备了完备的并发安全防护。

---

## 🌟 核心功能模块与 AI 系统设计

### 1. 多 Agent 市场对抗与生存博弈
在 [Simulation/agents.py](Simulation/agents.py) 中，系统每日循环模拟以下核心智能体行为：
- **市场 Agent**：每日有 50% 概率联网 DuckDuckGo 搜索最新的消费电子或半导体行业动态（如芯片缺货、存储颗粒降价、AI 硬件热潮等），通过 LLM 自动将其转化为结构化的 `MarketEvent` 作用于整个生态。
- **品牌 Agent**：
  - **初始资金一致**：所有品牌（Apple、Xiaomi、Huawei、Lenovo）初始资金统一重置为 100,000.00 元，处于同一起跑线。
  - **进货与研发消耗**：品牌自动补仓、发起促销广告（花费 5,000 元）或限时闪购（花费 3,000 元）均会真实扣减其流动资金。当面临存货压力时，若资金充足（>= 25,000 元），品牌会自动投入 20,000 元进行 R&D 研发上架高竞争力的新一代产品；反之，若在售商品过多且滞销，会自动执行"优胜劣汰"下架竞争力最低的型号。
  - **破产清算机制**：若某品牌流动资金降低至 0 或负数，该品牌将立刻宣告"破产"，彻底退出市场一切广告、补货、研发及销售行为，退出竞争。
- **顾客 Agent**：基于马斯洛偏好与预算模型。每日以 60% 概率引入 1~2 名具有真实中国姓名、偏好、职业及对应预算的新顾客，使市场大盘随时间推移逐步增大。
- **分析 Agent（专属 AI 经营日报）**：每天结束时，遍历非破产品牌，提取其销售额、利润、流动资金、热销商品及今日动作，独立调用 Agnes API 生成一份专属经营分析日报，指导明日运作。

### 2. 联网真实价格校准
- 在新品发布阶段，AI 不再凭空给出荒谬的商品定价。
- 算法会联网检索该产品线的真实售价，通过正则表达式提取数值，并按品类（手机、电脑、耳机、手环/手表）的边界限制剔除异常干扰，求出基准参考价。
- 最终结合品牌独有的加价率（Premium/Aggressive 等策略）计算出合理的零售价，并以 60% 成本系数反推其生产成本。

### 3. 品牌 SVG Logo 系统
- 每个品牌 Agent 配备独立的 SVG 矢量 Logo（`static/images/logos/` 目录）。
- `BrandAgent.logo_url` 属性提供统一的 Logo 访问路径。
- 模板中通过 `<img src="{{ ba.logo_url }}" class="brand-logo-img">` 渲染，支持多种尺寸（商品卡片小图标、品牌专区大图标等）。

### 4. 数据大屏看板与分品牌日报中心
- **各品牌今日业绩大屏**：实时显示各品牌的今日销量、销售额、今日利润、流动资金与运营状态。破产的品牌将被置灰、标红，并打上"已破产"徽章。
- **专属日报 Tab 切换**：使用 Bootstrap Tab 页面切换并快速阅读今日各个品牌对应的 AI 日报（已破产品牌显示破产公告）。
- **日报中心侧边栏过滤**：支持根据品牌过滤其所有的历史日报。

### 5. 推进防抖与并发控制
- **后端线程锁**：在 `advance_day()` 主控入口处添加了 `threading.Lock`。若上一次模拟仍在运行，后续推进请求将直接拒绝，防止数据错乱。
- **前端物理防抖**：在用户点击"推进一天"时，前端立刻禁用按钮并呈现 `正在推演中...` 的动画加载状态，阻断重复提交。

---

## 🎨 前端设计系统

### 技术栈
- **CSS 框架**：Bootstrap 5.3 (CDN)
- **图表库**：Chart.js 4.4 (CDN)
- **图标库**：Bootstrap Icons 1.11 (CDN)

### 字体系统
| 用途 | 字体 | CSS 变量 |
|------|------|----------|
| 标题/Display | Outfit | `--font-display` |
| 正文/Body | Inter | `--font-body` |
| 数据/Mono | JetBrains Mono | `--font-mono` |

### 色彩体系
| 类别 | 变量 | 值 |
|------|------|-----|
| 主色 | `--primary` | `#2563eb` |
| 成功 | `--success` | `#16a34a` |
| 警告 | `--warning` | `#f59e0b` |
| 危险 | `--danger` | `#ef4444` |
| 信息 | `--info` | `#0891b2` |
| 背景 | `--bg-main` | `#f8fafc` |
| 卡片 | `--bg-card` | `#ffffff` |
| 侧边栏 | `--bg-sidebar` | `#f1f5f9` |

### 设计特点
- 亮色主题，Apple 风格极简设计
- 统一圆角系统（`--radius-btn: 10px`, `--radius-card: 16px`）
- 三级阴影系统（`--shadow-sm/md/lg`）
- 卡片交互：hover 上浮 + 边框变色 + 阴影加深
- 商品品牌标签：hover 时滑入显示

---

## 🛠️ 项目结构

```
onlineshop-main/
├── TechMall/              # Django 项目全局配置（settings.py, urls.py, wsgi.py）
├── Shop/                  # 基础电商应用（前台商城、购物车、订单、数据库模型）
│   ├── models.py          # Category, Product, Cart, Order, OrderItem
│   ├── views.py           # 商城业务视图（含真实订单向模拟模块的同步逻辑）
│   ├── urls.py            # 商城路由
│   └── management/commands/assign_brands.py  # 商品自动分配品牌
├── Simulation/            # AI 电商生态模拟应用（系统核心）
│   ├── agents.py          # 核心 Agent 算法、价格校准、联网事件及主推进循环
│   ├── models.py          # SimulationState, CustomerAgent, BrandAgent, MarketEvent, DailyReport, DailyStatistic, BrandDailyStatistic
│   ├── views.py           # 模拟大屏看板、品牌中心、日报中心及推进接口
│   └── urls.py            # 模拟系统路由
├── templates/             # HTML 模版目录（14 个模板文件）
│   ├── base.html          # 基础导航栏与共用模版
│   ├── index.html         # 商城首页（品牌专区 + 分类 + 商品）
│   ├── cart.html          # 购物车
│   ├── category.html      # 分类商品列表
│   ├── brand_zone.html    # 品牌专区详情页
│   ├── productDetail.html # 商品详情页（规格 + 竞争力评分）
│   ├── orderSubmit.html   # 订单结算
│   ├── orderSuccess.html  # 下单成功
│   ├── partials/product_card.html  # 商品卡片组件
│   └── simulation/        # 模拟系统模板
│       ├── dashboard.html     # 市场大屏
│       ├── brands.html        # 品牌中心
│       ├── customers.html     # 顾客中心
│       ├── reports.html       # AI 日报中心
│       └── events.html        # 市场事件中心
├── static/
│   └── css/style.css      # 亮色主题设计系统（Bootstrap 补充）
├── static/images/logos/   # 品牌 SVG Logo（apple.svg, xiaomi.svg, huawei.svg, lenovo.svg）
├── image/                 # 种子商品源图片（20 张，用于重置时复制到 media/）
├── media/products/        # 运行时商品图片（由 Django ImageField 管理）
├── scratch/               # 工具脚本
│   ├── reset_all_data.py  # 一键重置推演数据至 Day 1
│   └── fix_images.py      # 商品图片下载修复
├── replace_emojis.py      # Emoji → SVG Logo 迁移脚本
├── clean_svgs.py          # SVG 文件清理优化脚本
├── db.sqlite3             # SQLite 数据库
├── requirements.txt       # 依赖文件（Django 4.2+, Pillow 10.0+）
└── manage.py              # Django 管理入口
```

---

## ⚡ 快速启动与数据重置

### 1. 启动项目
```bash
# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移
python manage.py migrate

# 加载种子数据
python manage.py loaddata Shop/fixtures/initial_data.json

# 分配商品到品牌
python manage.py assign_brands

# 启动开发服务器
python manage.py runserver
```
- 商城首页：`http://127.0.0.1:8000/`
- AI 模拟市场大屏：`http://127.0.0.1:8000/simulation/dashboard/`

### 2. 配置 AI API
在 `TechMall/settings.py` 中配置 Agnes API Key：
```python
AGNES_API_KEY = "your-api-key-here"
AGNES_API_BASE = "https://apihub.agnes-ai.com/v1"
AGNES_MODEL = "agnes-2.0-flash"
AGNES_IMAGE_MODEL = "agnes-image-2.1-flash"
```

### 3. 重置推演数据至 Day 1
一键重置脚本将自动完成：
- 清空所有模拟订单、事件、日报、统计数据
- 从 fixture 恢复 20 款种子商品
- 从 `image/` 复制商品图片到 `media/products/`
- 重置 4 个品牌 Agent 资金与状态
- 播种 10 名种子顾客
- 自动分配商品到对应品牌

```bash
python scratch/reset_all_data.py
```

---

## 🔧 管理命令

| 命令 | 说明 |
|------|------|
| `python manage.py assign_brands` | 根据商品名称关键词自动分配到品牌 Agent |
| `python manage.py loaddata Shop/fixtures/initial_data.json` | 加载种子商品数据 |
| `python scratch/reset_all_data.py` | 一键重置推演数据至 Day 1 |
