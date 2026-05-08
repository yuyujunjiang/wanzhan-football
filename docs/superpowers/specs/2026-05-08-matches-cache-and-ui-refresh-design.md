---
title: "赛程赛果：UI 精简 + 今日动态刷新 + 本地缓存（JSON）"
date: "2026-05-08"
status: "draft"
---

## 背景与目标

当前赛程/赛果数据来自 `SportteryResultsProvider`，每次请求都会实时拉取上游数据。用户希望：

- **页面更简洁**：每场比赛只展示赔率（不需要按钮区域）。
- **默认主页面**：取消一级首页，打开网站默认进入 `matches`。
- **更快**：赛程固定信息本地缓存；赔率实时变化、赛果更新频繁，需要分频刷新。

本设计的目标是在不引入复杂数据建模的前提下：

- 打开页面尽量“秒开”（读本地缓存）
- 今日比赛动态信息保持新鲜（赔率 30 分钟；赛果 5 分钟）
- 避免并发请求导致的“刷新风暴”（同一天只允许一次刷新在飞）

## 范围（In / Out）

- **In**
  - `/matches` 与 `/wanzhan/matches` 列表 UI 精简：只展示赔率信息，不展示底部按钮
  - 根路由 `/` 重定向到 `/matches`
  - 后端增加 **按天 JSON 缓存**（含固定/动态分区）
  - 今日动态刷新：**赔率 30 分钟**、**赛果 5 分钟**（都只刷新今天）
  - 对“同一天刷新”做去重/锁，避免并发放大

- **Out（暂不做）**
  - 历史日期的动态刷新（赔率/赛果）
  - 完整的数据库表结构化落库（fixtures/results/odds 分表）
  - 复杂筛选（按联赛、热度、关注等）

## 数据分层与刷新策略

### 定义

- **固定信息（fixed）**：一天内基本不变
  - `matchId`、`date`、`league`、`homeTeam`、`awayTeam`、`kickoffTime`、`matchStatus`（可选）
- **动态信息（dynamic）**：变化频繁
  - odds：`had`、`hhad`
  - results：`finalScore`、`halfScore`、`goalLine`、`outcomeSPF`、`outcomeRQSPF`
  - `fetchedAtOdds`、`fetchedAtResults`

### 刷新频率（仅今天）

- **赔率（odds）**：30 分钟 TTL
- **赛果（results）**：5 分钟 TTL
- 对非今天的日期：只读缓存（或首次无缓存时拉一次后落盘），**不做周期刷新**

### 并发去重（避免刷新风暴）

对每个 `date` 维护内存级“刷新锁”：

- 如果当前日期正在刷新 odds/results：
  - 其他请求直接返回当前缓存内容（不重复发起上游请求）
- 刷新完成后更新 JSON，并释放锁

> 备注：单进程 FastAPI dev/单实例部署可用；若未来多实例，需要分布式锁（Out of scope）。

## 缓存落盘格式与目录

### 目录

- `apps/api/data/matches/`
  - 例如：`apps/api/data/matches/2026-05-08.json`

### JSON 结构（按天）

```json
{
  "date": "2026-05-08",
  "fixed": [
    {
      "matchId": 123456,
      "date": "2026-05-08",
      "league": "英超",
      "homeTeam": "A",
      "awayTeam": "B",
      "kickoffTime": "2026-05-08 20:00:00",
      "matchStatus": "Selling"
    }
  ],
  "dynamic": {
    "fetchedAtOdds": "2026-05-08T21:00:00+08:00",
    "fetchedAtResults": "2026-05-08T21:03:00+08:00",
    "byMatchId": {
      "123456": {
        "had": { "h": "1.88", "d": "3.20", "a": "3.90" },
        "hhad": { "goalLine": "-1", "h": "2.65", "d": "3.35", "a": "2.25" },
        "finalScore": "1:0",
        "halfScore": "0:0",
        "goalLine": "-1",
        "outcomeSPF": "胜",
        "outcomeRQSPF": "让平"
      }
    }
  }
}
```

### 读取/合并为 API 响应

API 最终仍对前端返回“matches list”，每条 match 合并 fixed + dynamic：

- 以 `matchId` 为主键合并（如果缺少 matchId，则退化为 matchKey，但当前 provider 已提供 matchId）

## API 设计

### 现有

- `GET /api/matches?date=YYYY-MM-DD` -> `list[match]`

### 维持兼容 & 扩展

- `GET /api/matches?date=...`
  - 行为：优先读缓存；若 date 是今天则按 TTL 刷新动态字段（带锁去重）
- `GET /api/matches/range?start=YYYY-MM-DD&days=7`
  - 行为：按天分组返回，内部对每一天调用上面的逻辑
  - 返回：`[{ date, matchCount, matches: [...] }, ...]`

## 前端 UI 变更

### 1) 列表项只展示赔率（取消按钮）

- `/matches`
  - 移除底部按钮/入口（例如“去上传”等），只保留比赛信息与赔率展示
  - 赔率展示：HAD 与 HHAD 直接显示（不再需要“展开/收起”按钮；或保留小折叠但无额外动作按钮）

- `/wanzhan/matches`
  - 同样移除“详情/关联票”“添加彩票”按钮
  - 保留头部 `WanzhanShell`、日期选择、StatStrip

### 2) 取消一级首页

- 根路由 `/`：重定向到 `/matches`
  - 方式：Next.js App Router 使用 `redirect("/matches")`（服务器端重定向）

## 错误处理与回退

- 上游请求失败：
  - 若有旧缓存：返回旧缓存（并在响应中可选加入 `stale: true` 标记，前端可提示）
  - 若无缓存：返回 502/500（保持现有错误展示）

## 测试与验证

- **后端**
  - 单元测试：range 仍可用
  - 新增：缓存读写、TTL 判断、并发去重（可用简单的“锁命中”测试）
- **前端**
  - `npm run build` 通过
  - 视觉检查：列表无按钮，仅赔率；根路由自动进入 `/matches`

## 后续扩展（非本次）

- 多实例部署：分布式锁（Redis）+ 缓存共享
- 赛果状态更智能：开赛前/进行中/终场后不同刷新频率
- 历史数据归档与查询

