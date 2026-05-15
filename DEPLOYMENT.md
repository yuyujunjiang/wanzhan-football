# 足球计算器云服务器部署步骤

本文档适用于当前项目结构：

- 前端：`apps/web`，Next.js 15，默认端口 `3000`
- 后端：`apps/api`，FastAPI，默认端口 `8000`
- 反向代理：Nginx，公网访问 `80/443`
- 进程托管：systemd
- 默认部署目录：`/srv/wanzhan-football`
- 默认分支：`feature/football-calculator-mvp`

## 1. 准备云服务器

推荐环境：

- Ubuntu 22.04 或 24.04
- 2C4G 起步，若启用 PaddleOCR，建议 4G 内存以上
- 安全组放行：`22`、`80`、`443`
- 域名 DNS A 记录指向服务器公网 IP，例如 `yujj.club`

登录服务器：

```bash
ssh ubuntu@你的服务器IP
```

## 2. 首次部署

项目已经提供一键部署脚本：`scripts/deploy-ubuntu.sh`。

在服务器执行：

```bash
git clone https://github.com/yuyujunjiang/wanzhan-football.git
cd wanzhan-football
git checkout feature/football-calculator-mvp
sudo bash scripts/deploy-ubuntu.sh
```

脚本会自动完成：

- 安装 Nginx、Git、curl、Python、venv
- 安装或升级 Node.js 20
- 拉取指定分支到 `/srv/wanzhan-football/repo`
- 执行 `apps/web` 的 `npm ci` 和 `npm run build`
- 创建 FastAPI 虚拟环境并安装 `apps/api`
- 创建并启动 systemd 服务
- 配置 Nginx，把 `/` 转发到 Next.js，把 `/api/` 转发到 FastAPI

## 3. 配置后端环境变量

首次部署后，在服务器创建 API 环境文件：

```bash
sudo tee /srv/wanzhan-football/repo/apps/api/.env >/dev/null <<'EOF'
FC_SQLITE_PATH=data/app.sqlite3
FC_OCR_PROVIDER=stub
FC_RESULTS_PROVIDER=sporttery
FC_MATCHES_SCHEDULER_ENABLED=true
FC_MATCHES_SCHEDULER_INTERVAL_SECONDS=300
FC_MATCHES_SCHEDULER_FULL_REFRESH_SECONDS=1800
FC_COOKIE_SECURE=1
FC_CORS_ORIGINS=https://yujj.club,https://www.yujj.club
EOF
```

（将 `yujj.club` 换成你的域名。前端构建时 **不要** 设置 `NEXT_PUBLIC_API_BASE_URL`，让浏览器走同源 `/api/...`，由 Nginx 反代到 FastAPI。）

然后重启后端：

```bash
sudo systemctl restart football-calculator-api
```

说明：

- `FC_OCR_PROVIDER=stub`：先用占位 OCR，部署轻、启动快。
- `FC_OCR_PROVIDER=paddle`：启用 PaddleOCR，但服务器需要更多内存，首次安装依赖更慢。
- `FC_RESULTS_PROVIDER=sporttery`：使用竞彩数据源。
- 若需要使用 football-data.org，可改为 `FC_RESULTS_PROVIDER=football_data_org` 并增加 `FC_FOOTBALL_DATA_ORG_TOKEN=你的token`。

## 4. 万站登录与首个账号

万站（`/wanzhan/*`）已启用登录门禁：未登录会跳转到 `/wanzhan/login`。登录态为 HttpOnly Cookie（`fc_session`，有效期 30 天），记账本 API（`/api/ledger/*`）按登录用户隔离数据。

**不开放自助注册**，账号需在服务器上用 CLI 手工创建。首次部署后至少创建一个用户：

```bash
cd /srv/wanzhan-football/repo/apps/api
sudo -u www-data ./.venv/bin/python -m app.tools.create_user \
  --username admin \
  --password '请换成强密码'
```

说明：

- 将 `www-data` 换成你实际运行 `football-calculator-api` 的系统用户（与 `deploy-ubuntu.sh` 中 `SERVICE_USER` 一致）。
- 用户名在库中会规范为小写；登录页输入不区分大小写。
- 用户名已存在时命令退出码非 0，不会覆盖密码。
- 避免把密码写进 shell 历史：可先 `read -s PW` 再传入，或使用临时 env（勿提交到 git）。

浏览器访问 `https://你的域名/wanzhan/matches`（或根路径 `/`，会重定向到赛程），用上述账号登录即可。登录后默认进入 **赛程赛果**；记账本在底部 Tab「记账本」。

**HTTPS 与 Cookie**

生产环境务必启用 HTTPS（见下一节）。Nginx 将 `/api/` 反代到 FastAPI 时，前后端应 **同源**（例如页面与 API 都是 `https://yujj.club`），这样浏览器才会在请求 `/api/*` 时带上 `fc_session`。

当前登录接口在设置 Cookie 时未强制 `Secure` 标志；在纯 HTTP 内网调试时可正常登录。若你已在公网启用 HTTPS，建议在后续版本为生产环境开启 `Secure` Cookie（仅 HTTPS 传输），或在反向代理层确保全程 TLS，避免会话 Cookie 明文传输。

**升级注意（已有 SQLite）**

若服务器上在接入用户系统之前已有记账本数据，新版本迁移会 **清空** 旧 `ledger_tickets` / `ledger_legs` 后增加 `user_id` 列（与产品决策一致：上线后账本从空开始）。重要数据请先备份：

```bash
sudo cp /srv/wanzhan-football/repo/apps/api/data/app.sqlite3 \
  /srv/wanzhan-football/repo/apps/api/data/app.sqlite3.bak.$(date +%F)
```

## 5. 启用 HTTPS

确保域名已经解析到服务器，并且安全组放行 `80/443` 后执行：

```bash
cd wanzhan-football
sudo ENABLE_HTTPS=1 bash scripts/deploy-ubuntu.sh
```

脚本会安装 certbot 并申请 Let's Encrypt 证书。

## 6. 常用检查命令

检查前端服务：

```bash
sudo systemctl status football-calculator
sudo journalctl -u football-calculator -f
```

检查后端服务：

```bash
sudo systemctl status football-calculator-api
sudo journalctl -u football-calculator-api -f
```

检查 Nginx：

```bash
sudo nginx -t
sudo systemctl status nginx
```

检查接口：

```bash
curl http://127.0.0.1:8000/health
curl http://你的域名/health
curl "http://你的域名/api/matches/range?start=2026-05-15&days=1"
```

如果域名已启用 HTTPS：

```bash
curl https://你的域名/health
curl "https://你的域名/api/matches/range?start=2026-05-15&days=1"
```

## 7. 后续更新部署

代码合并到部署分支后，在服务器重新运行：

```bash
cd /srv/wanzhan-football/repo
sudo bash scripts/deploy-ubuntu.sh
```

如果你是在服务器已有仓库目录里直接部署，不想让脚本重新 clone：

```bash
cd /home/ubuntu/wanzhan-football
sudo USE_LOCAL_REPO=1 SERVICE_USER=ubuntu SERVICE_GROUP=ubuntu bash scripts/deploy-ubuntu.sh
```

## 8. 回滚

脚本会记录上一次 commit。需要回滚时执行：

```bash
cd /srv/wanzhan-football/repo
sudo bash scripts/rollback.sh
```

回滚后检查：

```bash
sudo systemctl status football-calculator
curl http://127.0.0.1:3000
```

## 9. 服务信息速查

- 前端 systemd：`football-calculator`
- 后端 systemd：`football-calculator-api`
- Nginx site：`/etc/nginx/sites-available/football-calculator`
- 代码目录：`/srv/wanzhan-football/repo`
- 前端目录：`/srv/wanzhan-football/repo/apps/web`
- 后端目录：`/srv/wanzhan-football/repo/apps/api`
- SQLite 默认位置：`/srv/wanzhan-football/repo/apps/api/data/app.sqlite3`

## 10. 常见问题

### 访问页面正常，但 API 404

检查 Nginx `/api/` 代理配置，应该保留 `/api` 前缀：

```nginx
location /api/ {
  proxy_pass http://127.0.0.1:8000;
}
```

修改后执行：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### API 启动失败

查看日志：

```bash
sudo journalctl -u football-calculator-api -n 200 --no-pager
```

常见原因：

- Python 版本低于 3.11
- PaddleOCR 依赖安装失败或内存不足
- `.env` 配置错误

### 记账本 API 401 `Not authenticated`

常见原因：

1. **未登录或会话过期**：打开 `/wanzhan/login` 重新登录。
2. **本地开发把 API 指到 `:8000`**：若设置了 `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`，Cookie 会落在 8000 端口，页面在 3000 端口时记账本请求带不上会话。**请删掉该环境变量**，只用 Next 的 `/api` 反代（见 `apps/web/next.config.mjs`）。
3. **服务器代码未更新**：需包含 `feature/football-calculator-mvp` 上的 auth + ledger 鉴权；更新后 `systemctl restart football-calculator-api` 并重新 `npm run build` 前端。
4. **尚未建用户**：见上文「万站登录与首个账号」执行 `create_user`。

自检（已登录后，在浏览器同域执行）：

```bash
curl -sS -b "fc_session=你的cookie值" "https://你的域名/api/auth/me"
curl -sS -b "fc_session=你的cookie值" "https://你的域名/api/ledger/summary?start=2026-05-15&end=2026-05-15"
```

### 前端启动失败

查看日志：

```bash
sudo journalctl -u football-calculator -n 200 --no-pager
```

常见原因：

- Node.js 版本低于 20
- `npm ci` 失败
- `apps/web/.next-build` 构建产物不存在

