#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${DOMAIN:-yujj.club}"
REPO_URL="${REPO_URL:-https://github.com/yuyujunjiang/wanzhan-football.git}"
BRANCH="${BRANCH:-feature/football-calculator-mvp}"

APP_ROOT="${APP_ROOT:-/srv/wanzhan-football}"
REPO_DIR="${REPO_DIR:-$APP_ROOT/repo}"
WEB_DIR_REL="${WEB_DIR_REL:-apps/web}"
PORT="${PORT:-3000}"
SERVICE_NAME="${SERVICE_NAME:-football-calculator}"
NGINX_SITE_NAME="${NGINX_SITE_NAME:-football-calculator}"

# Users
SERVICE_USER="${SERVICE_USER:-www-data}"
SERVICE_GROUP="${SERVICE_GROUP:-www-data}"
GIT_USER="${GIT_USER:-$SERVICE_USER}"

# If set to 1, deploy using the repo that contains this script.
# This avoids cloning into /srv when you already have a checkout (e.g. /home/ubuntu/wanzhan-football).
USE_LOCAL_REPO="${USE_LOCAL_REPO:-0}"

# Set ENABLE_HTTPS=1 to attempt certbot issuance.
ENABLE_HTTPS="${ENABLE_HTTPS:-0}"

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "Please run as root (e.g. sudo bash scripts/deploy-ubuntu.sh)"
    exit 1
  fi
}

log() {
  printf "\n==> %s\n" "$1"
}

detect_web_dir_rel() {
  # Returns a WEB_DIR_REL value relative to $REPO_DIR.
  # Priority:
  # 1) $WEB_DIR_REL (if valid)
  # 2) apps/web
  # 3) 足球计算器/apps/web
  # 4) first match of */apps/web
  local cand

  cand="$WEB_DIR_REL"
  if [[ -f "$REPO_DIR/$cand/package.json" ]]; then
    echo "$cand"
    return
  fi

  cand="apps/web"
  if [[ -f "$REPO_DIR/$cand/package.json" ]]; then
    echo "$cand"
    return
  fi

  cand="足球计算器/apps/web"
  if [[ -f "$REPO_DIR/$cand/package.json" ]]; then
    echo "$cand"
    return
  fi

  # shellcheck disable=SC2010
  cand="$(sudo -u www-data bash -lc "cd \"$REPO_DIR\" && ls -d */apps/web 2>/dev/null | head -n 1" || true)"
  if [[ -n "$cand" && -f "$REPO_DIR/$cand/package.json" ]]; then
    echo "$cand"
    return
  fi

  return 1
}

ensure_packages() {
  log "Installing base packages (nginx, git, curl)"
  apt-get update -y
  apt-get install -y nginx git curl ca-certificates perl
}

ensure_node() {
  if command -v node >/dev/null 2>&1; then
    local major
    major="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo "")"
    if [[ "$major" =~ ^[0-9]+$ ]] && (( major >= 20 )); then
      log "Node.js already installed (node $(node -v))"
      return
    fi
    log "Node.js is installed but < 20 (node $(node -v)); upgrading to 20.x"
  else
    log "Installing Node.js 20.x"
  fi

  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
  log "Node.js installed: $(node -v), npm: $(npm -v)"
}

ensure_user_and_dirs() {
  log "Preparing directories under $APP_ROOT"
  mkdir -p "$APP_ROOT"
  mkdir -p "$REPO_DIR"
  chown -R "$SERVICE_USER:$SERVICE_GROUP" "$APP_ROOT"
}

resolve_repo_dir() {
  if [[ "$USE_LOCAL_REPO" == "1" ]]; then
    local script_dir repo_root
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    repo_root="$(git -C "$script_dir" rev-parse --show-toplevel 2>/dev/null || true)"
    if [[ -z "$repo_root" ]]; then
      echo "USE_LOCAL_REPO=1 but could not find a git repo from: $script_dir"
      exit 1
    fi
    REPO_DIR="$repo_root"
    log "Using local repo: $REPO_DIR"
  fi
}

clone_or_update_repo() {
  if [[ "$USE_LOCAL_REPO" == "1" ]]; then
    log "Skipping clone/pull (USE_LOCAL_REPO=1)"
    return
  fi

  log "Syncing repository ($REPO_URL @ $BRANCH)"

  if [[ ! -d "$REPO_DIR/.git" ]]; then
    rm -rf "$REPO_DIR"
    install -d -o "$GIT_USER" -g "$SERVICE_GROUP" "$REPO_DIR"
    sudo -u "$GIT_USER" git clone "$REPO_URL" "$REPO_DIR"
  fi

  local prev_commit_file="$APP_ROOT/.prev_commit"
  local last_good_file="$APP_ROOT/.last_good_commit"
  local current_commit=""

  if sudo -u "$GIT_USER" git -C "$REPO_DIR" rev-parse --verify HEAD >/dev/null 2>&1; then
    current_commit="$(sudo -u "$GIT_USER" git -C "$REPO_DIR" rev-parse HEAD)"
  fi

  sudo -u "$GIT_USER" git -C "$REPO_DIR" fetch --all --prune
  sudo -u "$GIT_USER" git -C "$REPO_DIR" checkout "$BRANCH"
  sudo -u "$GIT_USER" git -C "$REPO_DIR" pull --ff-only

  if [[ -n "$current_commit" ]]; then
    echo "$current_commit" > "$prev_commit_file"
  fi

  if [[ ! -f "$last_good_file" ]]; then
    # Initialize last_good to current HEAD (best effort).
    sudo -u "$GIT_USER" git -C "$REPO_DIR" rev-parse HEAD > "$last_good_file"
  fi
}

build_web() {
  WEB_DIR_REL="$(detect_web_dir_rel)" || {
    echo "Could not locate Next.js app directory (expected apps/web/package.json or 足球计算器/apps/web/package.json)."
    echo "Repo directory: $REPO_DIR"
    exit 1
  }

  echo "$WEB_DIR_REL" > "$APP_ROOT/.web_dir_rel"
  log "Installing deps and building Next.js app ($WEB_DIR_REL)"

  local web_dir="$REPO_DIR/$WEB_DIR_REL"
  if [[ ! -f "$web_dir/package.json" ]]; then
    echo "Expected $web_dir/package.json but not found."
    exit 1
  fi

  sudo -u "$SERVICE_USER" bash -lc "cd \"$web_dir\" && npm ci"
  sudo -u "$SERVICE_USER" bash -lc "cd \"$web_dir\" && npm run build"
}

write_systemd_service() {
  # Ensure we use the resolved WEB_DIR_REL.
  if [[ -f "$APP_ROOT/.web_dir_rel" ]]; then
    WEB_DIR_REL="$(cat "$APP_ROOT/.web_dir_rel" | tr -d '\n')"
  fi

  log "Configuring systemd service: $SERVICE_NAME"
  local unit="/etc/systemd/system/$SERVICE_NAME.service"

  cat > "$unit" <<EOF
[Unit]
Description=Football Calculator (Next.js)
After=network.target

[Service]
Type=simple
WorkingDirectory=$REPO_DIR/$WEB_DIR_REL
Environment=NODE_ENV=production
Environment=PORT=$PORT
ExecStart=/usr/bin/npm run start
Restart=always
RestartSec=3
User=$SERVICE_USER
Group=$SERVICE_GROUP

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable --now "$SERVICE_NAME"
  systemctl restart "$SERVICE_NAME"
}

write_nginx_site() {
  log "Configuring Nginx site: $NGINX_SITE_NAME for $DOMAIN"

  local site_available="/etc/nginx/sites-available/$NGINX_SITE_NAME"
  cat > "$site_available" <<'EOF'
server {
  listen 80;
  server_name __DOMAIN__ www.__DOMAIN__;

  location / {
    proxy_pass http://127.0.0.1:__PORT__;
    proxy_http_version 1.1;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
  }
}
EOF

  # Fill in placeholders without relying on sed -i differences.
  perl -0777 -i -pe "s/__DOMAIN__/$DOMAIN/g; s/__PORT__/$PORT/g" "$site_available"

  ln -sf "$site_available" "/etc/nginx/sites-enabled/$NGINX_SITE_NAME"

  nginx -t
  systemctl reload nginx
}

maybe_enable_https() {
  if [[ "$ENABLE_HTTPS" != "1" ]]; then
    log "Skipping HTTPS (set ENABLE_HTTPS=1 to enable with certbot)"
    return
  fi

  log "Attempting HTTPS via certbot (Let's Encrypt)"
  apt-get install -y certbot python3-certbot-nginx

  # This will fail if DNS is not pointing to this server, or ports 80/443 blocked.
  certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN"

  systemctl status certbot.timer --no-pager || true
}

mark_last_good() {
  log "Marking current commit as last known good"
  if [[ -d "$REPO_DIR/.git" ]]; then
    sudo -u "$GIT_USER" git -C "$REPO_DIR" rev-parse HEAD > "$APP_ROOT/.last_good_commit"
  fi
}

main() {
  require_root
  ensure_packages
  ensure_node
  resolve_repo_dir
  ensure_user_and_dirs
  clone_or_update_repo
  build_web
  write_systemd_service
  write_nginx_site
  maybe_enable_https
  mark_last_good

  log "Done"
  echo "- App: http://$DOMAIN (HTTPS if enabled)"
  echo "- Service: systemctl status $SERVICE_NAME"
  echo "- Logs: journalctl -u $SERVICE_NAME -f"
}

main "$@"

