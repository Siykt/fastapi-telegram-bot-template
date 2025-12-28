# FastAPI Telegram Bot Template

一个基于 FastAPI 和 aiogram 的 Telegram Bot 后端模板项目，提供完整的项目结构和最佳实践。

## 📋 目录

- [技术栈](#技术栈)
- [功能特性](#功能特性)
- [项目结构](#项目结构)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [运行方式](#运行方式)
- [数据库迁移](#数据库迁移)
- [开发指南](#开发指南)
- [API 文档](#api-文档)
- [部署](#部署)

## 🛠 技术栈

| 类型         | 选型        | 版本要求     |
| ------------ | ----------- | ------------ |
| 语言         | Python      | 3.11+        |
| Web 框架     | FastAPI     | 0.100+       |
| ORM          | SQLAlchemy  | 2.0+ (async) |
| 数据库       | MySQL       | 8.0+         |
| 缓存         | Redis       | 7.0+         |
| 数据校验     | Pydantic    | 2.0+         |
| YAML         | PyYAML      | 6.0.2+       |
| Telegram Bot | aiogram     | 3.21+        |
| APScheduler  | APScheduler | 3.11+        |
| 日志框架     | loguru      | 0.7.0+       |
| 数据库迁移   | Alembic     | 1.13+        |

## ✨ 功能特性

- 🚀 **异步架构**: 基于 FastAPI 和 SQLAlchemy 2.0 的异步编程模型
- 🤖 **多 Bot 支持**: 支持同时管理多个 Telegram Bot
- 📝 **Webhook/Polling**: 支持 Webhook 和 Polling 两种运行模式
- 🗄️ **数据库迁移**: 使用 Alembic 进行数据库版本管理
- 📊 **结构化日志**: 基于 loguru 的彩色日志输出
- ⚙️ **环境配置**: 支持多环境配置（dev/test/prod）
- 🔒 **安全认证**: 内置 JWT 和 HMAC 签名验证
- 📦 **雪花 ID**: 分布式 ID 生成器
- 🧪 **测试支持**: 集成 pytest 测试框架

## 📁 项目结构

```
fastapi-telegram-bot-template/
├── app/
│   ├── __init__.py
│   ├── api/                       # API 路由层
│   │   ├── __init__.py
│   │   ├── dependencies.py        # 依赖注入
│   │   └── telegram_router.py     # Telegram Webhook 路由
│   ├── bot/                       # Telegram Bot 代码
│   │   ├── __init__.py
│   │   ├── bot_manager.py         # Bot 管理器
│   │   ├── keyboards.py           # 键盘组件
│   │   ├── middlewares.py         # 中间件
│   │   └── handlers/              # 消息处理器
│   │       ├── __init__.py
│   │       └── common.py          # 通用处理器
│   ├── core/                      # 核心模块（配置、数据库、日志等）
│   │   ├── __init__.py
│   │   ├── config.py              # 配置管理
│   │   ├── database.py            # 数据库连接
│   │   ├── logger.py              # 日志配置
│   │   └── redis.py               # Redis 连接
│   ├── models/                    # 数据模型 (SQLAlchemy)
│   │   ├── __init__.py
│   │   └── base.py                # 模型基类
│   ├── schemas/                   # Pydantic 模型
│   │   └── __init__.py
│   ├── services/                  # 业务服务层
│   │   └── __init__.py
│   └── utils/                     # 工具函数
│       ├── __init__.py
│       ├── security.py            # 安全工具（HMAC签名等）
│       └── snowflake.py           # 雪花ID生成器
├── main.py                        # 应用入口
├── alembic/                       # 数据库迁移
│   ├── env.py                     # Alembic 环境配置
│   ├── script.py.mako             # 迁移脚本模板
│   └── versions/                  # 迁移版本文件
├── alembic.ini                    # Alembic 配置文件
├── tests/                         # 测试目录
│   └── __init__.py
├── deploy/                        # 部署相关
├── docs/                          # 文档目录
├── base.config.yml                # 基础配置
├── dev.config.yml                 # 开发环境配置（可选）
├── test.config.yml                # 测试环境配置（可选）
├── prod.config.yml                # 生产环境配置（可选）
├── requirements.txt               # Python 依赖
├── pyproject.toml                 # 项目配置
└── README.md                      # 项目说明
```

## 🔧 环境要求

- Python 3.11+
- MySQL 8.0+
- Redis 7.0+

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd fastapi-telegram-bot-template
```

### 2. 创建虚拟环境

```bash
# 使用 conda
conda create -n telegram-bot python=3.11
conda activate telegram-bot

# 或使用 venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
# 使用 pip
pip install -r requirements.txt

# 或使用 uv
uv pip install -r requirements.txt
```

### 4. 配置环境

复制并编辑配置文件：

```bash
cp base.config.yml dev.config.yml
```

编辑 `dev.config.yml`，配置以下内容：

- 数据库连接信息
- Redis 连接信息
- Telegram Bot Token
- 其他必要的配置项

### 5. 初始化数据库

```bash
# 创建数据库（MySQL）
mysql -u root -p
CREATE DATABASE fastapi_telegram_bot_template CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 运行数据库迁移
alembic upgrade head
```

### 6. 运行应用

```bash
# 开发模式
python main.py

# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

应用启动后，访问：
- API 文档: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

## ⚙️ 配置说明

项目使用 YAML 配置文件，支持多环境配置。配置文件按以下优先级加载：

1. `base.config.yml` - 基础配置（所有环境共享）
2. `{env}.config.yml` - 环境特定配置（覆盖基础配置）

通过环境变量 `APP_ENV` 指定当前环境（默认为 `dev`）：

```bash
export APP_ENV=dev    # 开发环境
export APP_ENV=test   # 测试环境
export APP_ENV=prod   # 生产环境
```

### 配置项说明

#### 基础配置

```yaml
app_name: FastApiTelegramBotTemplate  # 应用名称
secret_key: jwt_secret_key            # JWT 密钥（生产环境请修改）
debug: true                           # 调试模式
```

#### 数据库配置

```yaml
database:
  url: 'mysql+asyncmy://user:pass@localhost:3306/database_name'
  pool_size: 10                       # 连接池大小
  max_overflow: 20                    # 最大溢出连接数
  pool_timeout: 30                    # 连接超时时间（秒）
  echo: false                         # 是否打印 SQL 语句
```

#### Redis 配置

```yaml
redis:
  url: redis://localhost:6379/0
```

#### Bot 配置

```yaml
bots:
  - name: '@your_bot_name'
    token: 'your_telegram_bot_token'
    mode: 'polling'                   # polling 或 webhook
    webhook_url: 'https://your-domain.com/webhook'  # webhook 模式必填
    bot_url: 'https://t.me/your_bot'
    app_url: 'https://your-miniapp-url.com'
```

#### 日志配置

```yaml
log:
  level: INFO                         # DEBUG/INFO/WARNING/ERROR/CRITICAL
  format: '<green>{time:YYYY-MM-DD HH:mm:ss}</green> | ...'
  rotation: '10 MB'                   # 日志轮转大小
  retention: '7 days'                 # 日志保留时间
```

## 🏃 运行方式

### 开发模式

```bash
python main.py
```

### 生产模式

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 使用 systemd（Linux）

项目提供了 systemd 服务文件模板，位于 `deploy/self-project.service`。修改后复制到系统目录：

```bash
sudo cp deploy/self-project.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable self-project
sudo systemctl start self-project
```

## 🗄️ 数据库迁移

### 创建迁移

```bash
alembic revision --autogenerate -m "描述信息"
```

### 应用迁移

```bash
# 升级到最新版本
alembic upgrade head

# 升级到指定版本
alembic upgrade <revision>

# 降级到指定版本
alembic downgrade <revision>
```

### 查看迁移历史

```bash
alembic history
```

## 💻 开发指南

### 代码规范

项目使用 `ruff` 进行代码检查和格式化：

```bash
# 检查代码
ruff check .

# 格式化代码
ruff format .
```

### 添加新的 Bot 处理器

1. 在 `app/bot/handlers/` 目录下创建新的处理器文件
2. 在 `app/bot/__init__.py` 中注册处理器

### 添加新的 API 路由

1. 在 `app/api/` 目录下创建新的路由文件
2. 在 `main.py` 中注册路由

### 添加新的数据模型

1. 在 `app/models/` 目录下创建模型文件
2. 创建对应的 Alembic 迁移文件
3. 在 `app/schemas/` 目录下创建对应的 Pydantic 模型

### 运行测试

```bash
pytest
```

## 📚 API 文档

启动应用后，访问以下地址查看 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

> 注意：生产环境下 API 文档默认关闭，可通过配置 `debug: true` 启用。

## 🚢 部署

### Docker 部署

```bash
# 构建镜像
docker build -t telegram-bot .

# 运行容器
docker run -d -p 8000:8000 --env-file .env telegram-bot
```

### 环境变量

生产环境建议使用环境变量覆盖敏感配置：

```bash
export APP_ENV=prod
export SECRET_KEY=your-production-secret-key
export DATABASE_URL=mysql+asyncmy://user:pass@host:3306/db
export REDIS_URL=redis://host:6379/0
```

## 📄 许可证

[MIT](LICENSE)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 联系方式

[Siykt](https://github.com/Siykt)

[Gavin](https://github.com/konbluesky)
