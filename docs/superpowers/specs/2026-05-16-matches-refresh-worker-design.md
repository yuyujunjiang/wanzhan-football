# 赛程赛果：独立刷新进程 + 比赛状态分流

**日期：** 2026-05-16  
**开发基线：** `.worktrees/football-calculator-mvp`（分支 `feature/football-calculator-mvp`）  
**状态：** 待实现（用户已确认设计）  
**取代/补充：** `2026-05-08-matches-cache-and-ui-refresh-design.md`（缓存格式延续，刷新架构升级）

---

## 1. 背景与目标

### 痛点（用户确认）

- 打开赛程页慢（请求路径可能同步打 Sporttery）
- API 与刷新逻辑耦合在同一 FastAPI 进程
- 另有数据新鲜度与前端体验问题；**最痛的是 A（慢）与 C（耦合）**

### 目标

1. **刷新完全独立**：常驻 `matches-worker` 进程写本地 JSON；API **只读缓存，请求绝不打 Sporttery**
2. **待结票结算独立**：第三个 `settlement-worker` 进程
3. **比赛状态规范化**：JSON 含 `phase`；赛程 / 赛果 Tab 按状态分流
4. **已开赛不可选赔**：赛程 Tab 内 `live` / `finished` 均禁用胜平负；开赛后展示比分
5. **前端无感**：不展示缓存时间；赛程仍约 60s 轮询读 API（只读 JSON，负担小）

---

## 2. 已确认的产品决策

| 项 | 决策 |
|----|------|
| API 读赛程 | 只读 `data/matches/*.json`；无缓存 → 200 + `[]`（与现空态一致） |
| 刷新部署 | 独立 systemd daemon：`football-calculator-matches-worker` |
| 结算 | 独立 systemd daemon：`football-calculator-settlement-worker`（与 matches 解耦） |
| 前端缓存提示 | 不展示「更新时间」 |
| 已开赛判定 | **OR**：开球时间已到 **或** Sporttery 状态表明已开赛/完场 |
| 推迟/取消 | **进赛果 Tab**（`phase = cancelled`，与 `finished` 一同在赛果列表展示） |
| 存储 | **仍按天一个 JSON**（不拆赛果独立文件）；用 `phase` 字段分流 |

---

## 3. 架构与进程边界

```
                    ┌─────────────────────────┐
                    │  Sporttery Web API      │
                    └───────────┬─────────────┘
                                │ HTTPS（仅 worker）
                    ┌───────────▼─────────────┐
                    │  matches-worker         │
                    │  写 data/matches/*.json │
                    └───────────┬─────────────┘
                                │ 只读
                    ┌───────────▼─────────────┐
                    │  FastAPI (API)          │
                    │  GET /api/matches*      │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Next.js 赛程/赛果页    │
                    └─────────────────────────┘

┌─────────────────────────┐
│  settlement-worker      │──► SQLite ledger（待结票结算）
│  读 JSON + DB           │
└─────────────────────────┘
```

| 进程 | 入口（示意） | 职责 | 禁止 |
|------|-------------|------|------|
| **API** | `uvicorn app.main:app` | 读 JSON；票据/OCR/记账本/登录 | 打 Sporttery；写 matches 缓存；周期刷新 |
| **matches-worker** | `python -m app.workers.matches_refresh` | 拉 Sporttery、算 `phase`、写 JSON | HTTP；ledger 结算 |
| **settlement-worker** | `python -m app.workers.ledger_settlement` | `settle_pending_tickets()` | 打 Sporttery；写 JSON |

### 从 API 移除

- `main.py` 中 `start_matches_scheduler` / `stop_matches_scheduler`
- `CachedSportteryResultsProvider.list_matches` 内读时 TTL 刷新与进程内写锁
- 环境变量 `FC_MATCHES_SCHEDULER_*` 对 API 无意义（可保留给 worker 复用或改名为 worker 专用前缀）

### 保留

- `SportteryResultsProvider`：**仅** matches-worker 调用
- 按天 JSON 的 `fixed` + `dynamic` 结构（见 §4）

---

## 4. 缓存格式（按天 JSON）

路径：`{FC_MATCHES_CACHE_DIR}/{YYYY-MM-DD}.json`（默认 `data/matches/`）

```json
{
  "date": "2026-05-16",
  "fixed": [
    {
      "matchId": 123456,
      "date": "2026-05-16",
      "league": "英超",
      "homeTeam": "A",
      "awayTeam": "B",
      "kickoffTime": "2026-05-16 20:00:00",
      "matchStatus": "Selling"
    }
  ],
  "dynamic": {
    "fetchedAtOdds": "2026-05-16T18:00:00+08:00",
    "fetchedAtResults": "2026-05-16T18:05:00+08:00",
    "byMatchId": {
      "123456": {
        "phase": "not_started",
        "had": { "h": "1.88", "d": "3.20", "a": "3.90" },
        "hhad": { "goalLine": "-1", "h": "2.65", "d": "3.35", "a": "2.25" },
        "finalScore": null,
        "halfScore": null,
        "goalLine": "-1",
        "outcomeSPF": null,
        "outcomeRQSPF": null
      }
    }
  },
  "meta": { "createdAt": "...", "updatedAt": "..." }
}
```

### `phase` 枚举

| 值 | 含义 | 赛程 Tab | 赛果 Tab |
|----|------|:--------:|:--------:|
| `not_started` | 未开赛 | ✅ | ❌ |
| `live` | 已开赛、未终场 | ✅ | ❌ |
| `finished` | 已完赛 | ❌ | ✅ |
| `cancelled` | 推迟/取消/异常终止 | ❌ | ✅ |

合并为 API 列表项时，每条 match 必须带 **`phase`**（及原有展示字段）。

### `phase` 计算规则（worker 写入；API 对「今天」可读时重算）

**优先级：**

1. **取消/推迟**：`matchStatus` 或 Sporttery 结果态含 取消/推迟/中断/腰斩 等 → `cancelled`
2. **完场**：有非空 `finalScore`，或 `matchStatus` 含 完/结束/终场/FT 等 → `finished`
3. **已开赛（OR）** — 满足任一 → `live`：
   - 今日且 `now >= kickoffTime`（可解析时）
   - `matchStatus` 含 进行/直播/上半场/下半场 或英文 live 等
4. 否则 → `not_started`

**API 读时重算（仅 `date === today`）：** 使用服务器当前时间与缓存内原始字段，**不请求上游**；用于开球后数分钟内 worker 尚未刷新时，赛程 Tab 仍能及时禁用选赔。

---

## 5. matches-worker 刷新策略

- **今天**
  - 赛果类（比分、`phase`、`outcome*`）：TTL **5 分钟**
  - 赔率（`had`/`hhad`）：TTL **30 分钟**
  - 实现可一次调用 `SportteryResultsProvider.list_matches(date)` 后拆分更新两类时间戳，减少上游压力
- **非今天**：仅在「全量周期」刷新（默认每 **30 分钟**）：今天、明天、过去 7 天
- **启动**：立即执行一轮 today + 全量日期，缩短冷启动空列表
- **并发**：进程内 `(date, kind)` 锁，同日期同 kind 不重叠刷新
- **失败**：保留旧 JSON；日志记录；下一轮重试

### 环境变量（建议）

| 变量 | 默认 | 说明 |
|------|------|------|
| `FC_MATCHES_CACHE_DIR` | `data/matches` | 与 API 共享 |
| `FC_RESULTS_PROVIDER` | `sporttery` | worker 使用 |
| `FC_MATCHES_WORKER_ODDS_TTL_SECONDS` | `1800` | 今天赔率 |
| `FC_MATCHES_WORKER_RESULTS_TTL_SECONDS` | `300` | 今天赛果/phase |
| `FC_MATCHES_WORKER_LOOP_SECONDS` | `60` | 主循环 sleep |
| `FC_MATCHES_WORKER_FULL_REFRESH_SECONDS` | `1800` | 全量日期刷新间隔 |

---

## 6. API 行为

### `GET /api/matches?date=YYYY-MM-DD`

- 读缓存 → 合并 `fixed` + `dynamic` → 返回 `list[match]`
- 无文件或损坏：`[]`
- 对 **今天**：对每条 match 执行 §4 的 phase 重算后再返回（可选：查询参数 `view=schedule|results` 由服务端过滤，减少前端负担；若未实现则前端过滤）

### `GET /api/matches/range?start=...&days=...`

- 按天调用上述逻辑，返回 `[{ date, matchCount, matches }, ...]`

### `get_results_by_match_keys`（票据结算）

- 从 JSON 缓存按 `matchKey` / `matchId` 查找；**不打 Sporttery**

### Provider 类

- 新增 **`CacheOnlyMatchesProvider`**（只读 JSON + 可选今日 phase 重算）
- API `get_results_provider()` 在 `sporttery` 配置下返回 `CacheOnlyMatchesProvider`，**不再**在请求链上使用 `CachedSportteryResultsProvider` 的写路径

---

## 7. settlement-worker

- 入口：`python -m app.workers.ledger_settlement`
- 循环间隔：默认 **120s**（可配置 `FC_SETTLEMENT_WORKER_INTERVAL_SECONDS`）
- 调用：从 `routes/ledger` 抽出的 `settle_pending_tickets()`（读 SQLite + matches JSON 赛果）
- **不**打 Sporttery、**不**写 matches JSON

---

## 8. 前端：`/wanzhan/matches`

### Tab 过滤

| Tab | 过滤条件 |
|-----|----------|
| **赛程** | `phase === 'not_started' \|\| phase === 'live'` |
| **赛果** | `phase === 'finished' \|\| phase === 'cancelled'` |

赛果 Tab 仍请求 `range`（近 7 天），按 `phase` 过滤，不再仅依赖 `finalScore` 非空。

### 赛程卡片展示

| phase | 比分区 | 角标 | 胜平负 |
|-------|--------|------|--------|
| `not_started` | 不显示 | 未开赛 | 可选 |
| `live` | 优先 `finalScore`；否则展示 `halfScore`；都无则「—」 | 已开赛 | **全部禁用** |
| `cancelled` / `finished` | （不在赛程 Tab 出现） | — | — |

### 交互

- `hasMatchStarted` ≡ `phase !== 'not_started'`（赛程 Tab 内与 `live` 禁用逻辑一致）
- 轮询发现某场已开赛：从 `selected` 移除该场
- 仍约 **60s** 轮询 `GET /api/matches`；不展示缓存更新时间

### 类型

- `MatchItem` 增加 `phase?: 'not_started' | 'live' | 'finished' | 'cancelled'`

### 共享逻辑

- `apps/web/src/lib/matchDisplay.ts`：`computePhase()` / `hasMatchStarted()` / `phaseLabel()`（含 `cancelled` → 「推迟/取消」）
- 后端 `app/domain/matches/phase.py` 镜像同一规则，供 worker 与 API 测试

---

## 9. 部署

### systemd 单元（与 API 同级 venv、`apps/api` 工作目录）

- `football-calculator-api` — 不变，**去掉** lifespan 内 scheduler
- `football-calculator-matches-worker` — 新增
- `football-calculator-settlement-worker` — 新增

### `deploy-ubuntu.sh` / `DEPLOYMENT.md`

- 增加两个 service 的安装与 `enable --now`
- 示例 env：关闭 API 侧 `FC_MATCHES_SCHEDULER_ENABLED`（或删除该变量）

---

## 10. 错误处理

| 场景 | 行为 |
|------|------|
| worker 上游失败 | 保留旧 JSON；日志 error |
| API 无缓存 | `[]`；赛程显示「暂无」 |
| phase 重算与 worker 不一致 | 以 API 今日重算为准（仅读缓存字段） |
| settlement 时无赛果 | 待结票保持 pending，下轮再试 |

---

## 11. 测试

### 后端

- `phase` 计算：开球 OR、完场、取消、边界时间
- `CacheOnlyMatchesProvider`：有/无缓存文件、合并 fixed+dynamic
- worker 锁：同 date/kind 不重复刷新（单元或集成）
- API 不再调用 upstream（mock provider 不被 list_matches 路径触发）

### 前端

- 赛程 Tab 不展示 `finished` / `cancelled`
- `live` 禁用选赔、显示比分
- 开赛后已选项被清除

---

## 12. 非目标（本版不做）

- 赛果 / 赛程物理分文件或分表
- Redis / 多实例分布式锁
- 前端展示「数据更新于」
- API 请求内冷启动拉 Sporttery（用户已拒绝）

---

## 13. 实现顺序建议

1. 抽取 `phase` 计算模块 + 测试  
2. `CacheOnlyMatchesProvider` + API 去掉 scheduler / 读时刷新  
3. `matches-worker` + systemd  
4. 前端 Tab 过滤 + 选赔禁用 + 比分展示  
5. `settlement-worker` + 抽离 settle 逻辑 + systemd  
6. 部署文档与 `deploy-ubuntu.sh`
