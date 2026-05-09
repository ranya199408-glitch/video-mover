# 部署指南 / Deployment Guide

## 方案：GitHub + Railway 自动部署

### 步骤 1：创建 GitHub 仓库

1. 在 GitHub 创建新仓库：`video-mover`
2. 本地初始化并推送：

```bash
cd video-mover
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/video-mover.git
git push -u origin main
```

### 步骤 2：获取 Railway Token

1. 注册 [Railway](https://railway.app)
2. 在 Railway Dashboard 创建新项目
3. 进入项目设置，获取 `RAILWAY_TOKEN`

### 步骤 3：配置 GitHub Secrets

在 GitHub 仓库设置中添加：

- `RAILWAY_TOKEN`: 你的 Railway API Token

### 步骤 4：触发部署

Push 代码到 main 分支，GitHub Actions 会自动：
1. 构建 Docker 镜像
2. 部署到 Railway

部署完成后，Railway 会提供公网 URL，如：`https://video-mover.up.railway.app`

### 前端配置

部署后端后，修改前端 API 地址：

```javascript
// qingdou-web/src/config.js 或相关文件
const API_BASE = 'https://your-railway-url.railway.app'
```

---

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行后端
uvicorn web.main:app --reload --port 8000

# 前端开发
cd qingdou-web
npm run dev
```

---

## 技术栈

- **后端**: FastAPI + OpenCV + Whisper
- **前端**: Vue 3 + TailwindCSS
- **部署**: Railway (Docker)
