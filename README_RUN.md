# 供应链智能预警与询价系统 (Supply Chain Agent) - 运行指南

本项目包含前后端分离的架构：后端基于 Python FastAPI + PostgreSQL，前端基于 Vue 3 + Element Plus。

## 1. 基础环境准备
在运行本项目之前，请确保您的计算机已安装以下基础环境：
- **Python**: 3.11 或以上版本
- **Node.js**: 18 或以上版本 (需包含 npm)
- **PostgreSQL**: 14 或以上版本 (需提前创建一个空数据库，例如命名为 `supply_chain_agent`)

## 2. 配置文件说明
项目根目录下需要一个 `.env` 配置文件（如果没有请新建）。这是系统连接数据库和初始化管理员的核心配置：

```env
# 数据库连接串 (请替换为实际的数据库账号、密码和IP)
DATABASE_URL=postgresql://postgres:你的密码@localhost:5432/supply_chain_agent

# JWT 签名密钥 (随意设置一个复杂的字符串即可)
SECRET_KEY=your_super_secret_key_string

# 系统初始化管理员账号与密码 (首次启动时会自动创建)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=Admin@123

# (可选) LLM 大模型配置
LLM_PROVIDER=openai
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
```

## 3. 后端启动 (Windows 示例)
*如果您使用 Linux/Mac，请将下面第一步中的 `.\venv\Scripts\activate` 替换为 `source venv/bin/activate`。*

打开终端，进入项目根目录：

```bash
# 1. 创建并激活虚拟环境
python -m venv venv
.\venv\Scripts\activate

# 2. 安装后端依赖
pip install -r requirements.txt

# 3. 启动后端服务
python main.py
```
> **提示**：首次运行 `python main.py` 时，系统会自动连接 PostgreSQL 并在空数据库中建立所需的 8 张核心数据表，同时根据 `.env` 中的配置创建管理员账号。
> 后端成功启动后，将运行在 `http://localhost:8000`。

## 4. 前端启动
再打开一个新的终端窗口，进入前端目录：

```bash
# 1. 进入前端文件夹
cd frontend

# 2. 安装前端依赖
npm ci

# 3. 启动前端开发服务器
npm run dev
```
> 前端启动后，终端会打印出本地访问地址（通常为 `http://localhost:5173/`）。
> 在浏览器打开该地址，使用您在 `.env` 中配置的管理员账号即可登录系统。

## 5. 核心功能测试验证
1. **采购员端**：使用管理员/采购员账号登录，进入 `预警看板` 模块，点击卡片右上角的“发送预警”。
2. **供应商端**：在前端注册一个供应商（或直接用后端数据库绑定的手机号登录），进入左侧 `发货预警` 模块，即可看到接收到的预警通知。
