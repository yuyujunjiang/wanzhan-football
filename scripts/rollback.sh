#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/srv/wanzhan-football}"
REPO_DIR="${REPO_DIR:-$APP_ROOT/repo}"
WEB_DIR_REL="${WEB_DIR_REL:-apps/web}"
SERVICE_NAME="${SERVICE_NAME:-football-calculator}"
SERVICE_USER="${SERVICE_USER:-www-data}"
GIT_USER="${GIT_USER:-$SERVICE_USER}"

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "Please run as root (e.g. sudo bash scripts/rollback.sh)"
    exit 1
  fi
}

log() {
  printf "\n==> %s\n" "$1"
}

main() {
  require_root

  local prev_file="$APP_ROOT/.prev_commit"
  local last_good_file="$APP_ROOT/.last_good_commit"
  local web_dir_rel_file="$APP_ROOT/.web_dir_rel"

  if [[ -f "$web_dir_rel_file" ]]; then
    WEB_DIR_REL="$(cat "$web_dir_rel_file" | tr -d '\n')"
  fi

  if [[ ! -d "$REPO_DIR/.git" ]]; then
    echo "Repo not found at $REPO_DIR"
    exit 1
  fi

  if [[ ! -f "$prev_file" ]]; then
    echo "No previous commit marker found at $prev_file"
    exit 1
  fi

  local prev_commit
  prev_commit="$(cat "$prev_file" | tr -d '\n' || true)"
  if [[ -z "$prev_commit" ]]; then
    echo "Previous commit marker is empty: $prev_file"
    exit 1
  fi

  log "Rolling back to $prev_commit"
  local current_commit
  current_commit="$(sudo -u "$GIT_USER" git -C "$REPO_DIR" rev-parse HEAD)"

  sudo -u "$GIT_USER" git -C "$REPO_DIR" fetch --all --prune
  sudo -u "$GIT_USER" git -C "$REPO_DIR" checkout "$prev_commit"

  log "Rebuilding web app"
  sudo -u "$SERVICE_USER" bash -lc "cd \"$REPO_DIR/$WEB_DIR_REL\" && npm ci"
  sudo -u "$SERVICE_USER" bash -lc "cd \"$REPO_DIR/$WEB_DIR_REL\" && npm run build"

  log "Restarting service: $SERVICE_NAME"
  systemctl restart "$SERVICE_NAME"

  log "Updating commit markers"
  echo "$current_commit" > "$prev_file"
  sudo -u "$GIT_USER" git -C "$REPO_DIR" rev-parse HEAD > "$last_good_file"

  log "Rollback complete"
  echo "- Service: systemctl status $SERVICE_NAME"
  echo "- Logs: journalctl -u $SERVICE_NAME -f"
}

main "$@"

