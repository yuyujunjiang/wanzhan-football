## Ubuntu 部署脚本（Next.js）

### 适用范围
- 域名：默认 `yujj.club`（可改）
- 仓库：默认 `https://github.com/yuyujunjiang/wanzhan-football.git`
- 分支：默认 `feature/football-calculator-mvp`
- 目录：默认部署到 `/srv/wanzhan-football`
- 服务：默认 systemd service 名称 `football-calculator`
- 端口：默认 `3000`（由 Nginx 反代到 80/443）

### 一键部署（HTTP）
在云主机上执行（需要 root）：

```bash
git clone https://github.com/yuyujunjiang/wanzhan-football.git
cd wanzhan-football
sudo bash scripts/deploy-ubuntu.sh
```

### 已有本地仓库：直接用当前目录部署（不再 clone 到 /srv）
适合你已经在 `/home/ubuntu/wanzhan-football` 有一份代码的情况：

```bash
cd /home/ubuntu/wanzhan-football
sudo USE_LOCAL_REPO=1 SERVICE_USER=ubuntu SERVICE_GROUP=ubuntu bash scripts/deploy-ubuntu.sh
```

### 说明：赛程/票据接口需要后端 API
脚本默认会同时部署 `apps/api`（FastAPI），并由 Nginx 反代到 `/api/*`（后端监听 `127.0.0.1:8000`）。

如果你的服务器暂时无法安装 Python 3.11，可先只部署前端：

```bash
sudo ENABLE_API=0 bash scripts/deploy-ubuntu.sh
```

### 一键部署 + HTTPS（Let's Encrypt）
确保 DNS A 记录已指向该主机且放行 80/443，然后：

```bash
sudo ENABLE_HTTPS=1 bash scripts/deploy-ubuntu.sh
```

### 自定义参数（可选）
```bash
sudo DOMAIN=yujj.club \
  BRANCH=feature/football-calculator-mvp \
  APP_ROOT=/srv/wanzhan-football \
  PORT=3000 \
  bash scripts/deploy-ubuntu.sh
```

### 回滚到上一次版本
```bash
sudo bash scripts/rollback.sh
```

