# Wanzhan Ledger Ticketing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build database-backed Wanzhan ticketing so users can select odds from schedule/results pages, create pending or immediately-settled tickets, automatically settle pending tickets, and view all ledger records from SQLite.

**Architecture:** Add a backend ledger module with SQLite tables, Pydantic models, settlement logic, and `/api/ledger` routes. Frontend replaces `localStorage` ledger calls with API calls and adds selectable odds, a confirmation sheet, and backend-powered ledger views. Settlement uses existing match/result provider data and runs both as an API/page fallback and a background scheduler hook.

**Tech Stack:** FastAPI, Pydantic, SQLite, pytest, Next.js App Router, React 19, TypeScript.

---

## File Structure

Backend:

- Create `apps/api/app/domain/ledger/models.py`: Pydantic request/response/domain models for ledger tickets and legs.
- Create `apps/api/app/domain/ledger/calculations.py`: stake, estimated payout, and profit helpers.
- Create `apps/api/app/domain/ledger/settlement.py`: result lookup and fixed `Nx1` settlement logic.
- Create `apps/api/app/storage/ledger_store.py`: SQLite persistence for ledger tickets and legs.
- Create `apps/api/app/routes/ledger.py`: `/api/ledger` routes.
- Modify `apps/api/app/storage/db.py`: add `ledger_tickets` and `ledger_legs` migrations.
- Modify `apps/api/app/main.py`: include ledger router and start ledger settlement background task.
- Modify or extend `apps/api/app/domain/results/scheduler.py`: call ledger settlement after match cache refresh.
- Test `apps/api/tests/test_ledger_calculations.py`.
- Test `apps/api/tests/test_ledger_store.py`.
- Test `apps/api/tests/test_ledger_api.py`.
- Test `apps/api/tests/test_ledger_settlement.py`.

Frontend:

- Modify `apps/web/src/lib/api.ts`: add ledger API types/client functions.
- Create `apps/web/src/lib/ledgerMath.ts`: frontend display-only estimated payout helper matching backend formula.
- Modify `apps/web/src/app/wanzhan/matches/page.tsx`: clickable odds, selection state, floating action, confirmation sheet, ledger submit.
- Modify `apps/web/src/lib/wanzhanLedger.ts`: either remove old `localStorage` use or leave only transitional helpers unused by pages.
- Modify `apps/web/src/app/wanzhan/ledger/page.tsx`: load summary and tickets from backend.
- Modify `apps/web/src/app/wanzhan/ledger/day/[date]/page.tsx`: load filtered tickets from backend.
- Create `apps/web/src/app/wanzhan/ledger/tickets/[id]/page.tsx`: ticket detail page for pending/settled ledger tickets.

## Baseline Notes

- Current Python test runner may crash locally with exit `139`; still write tests first and use targeted compile/API checks if pytest remains unavailable.
- Existing `apps/web/src/app/wanzhan/matches/page.tsx` is large. Keep edits focused; extract small local helpers if needed, but avoid broad UI rewrites.
- Current ledger is frontend-only `localStorage` in `apps/web/src/lib/wanzhanLedger.ts`; after this plan, ledger pages should read from backend APIs.

---

### Task 1: Backend Ledger Calculations

**Files:**

- Create: `apps/api/app/domain/ledger/__init__.py`
- Create: `apps/api/app/domain/ledger/calculations.py`
- Test: `apps/api/tests/test_ledger_calculations.py`

- [ ] **Step 1: Write failing calculation tests**

Create `apps/api/tests/test_ledger_calculations.py`:

```python
from app.domain.ledger.calculations import (
    compute_estimated_payout,
    compute_profit,
    compute_stake,
)


def test_fixed_nx1_stake_is_two_yuan_times_multiplier():
    assert compute_stake(multiplier=1) == 2.0
    assert compute_stake(multiplier=50) == 100.0


def test_fixed_nx1_estimated_payout_multiplies_all_selected_odds():
    assert compute_estimated_payout(sp_values=[1.75, 1.67], multiplier=50) == 292.25


def test_profit_is_payout_minus_stake():
    assert compute_profit(actual_payout=292.25, stake=100.0) == 192.25
    assert compute_profit(actual_payout=0.0, stake=100.0) == -100.0
```

- [ ] **Step 2: Run calculation tests and verify RED**

Run:

```bash
cd apps/api && uv run python -m pytest tests/test_ledger_calculations.py -q
```

Expected: FAIL because `app.domain.ledger.calculations` does not exist.

- [ ] **Step 3: Implement minimal calculation helpers**

Create `apps/api/app/domain/ledger/__init__.py` as an empty file.

Create `apps/api/app/domain/ledger/calculations.py`:

```python
from __future__ import annotations


def round2(value: float) -> float:
    return round(value + 1e-9, 2)


def compute_stake(*, multiplier: int) -> float:
    return round2(2.0 * multiplier)


def compute_estimated_payout(*, sp_values: list[float], multiplier: int) -> float:
    product = 1.0
    for sp in sp_values:
        product *= sp
    return round2(2.0 * multiplier * product)


def compute_profit(*, actual_payout: float, stake: float) -> float:
    return round2(actual_payout - stake)
```

- [ ] **Step 4: Run calculation tests and verify GREEN**

Run:

```bash
cd apps/api && uv run python -m pytest tests/test_ledger_calculations.py -q
```

Expected: PASS. If local pytest exits `139`, run:

```bash
cd apps/api && uv run python -m compileall app/domain/ledger/calculations.py
```

Expected: compile succeeds.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/domain/ledger/__init__.py apps/api/app/domain/ledger/calculations.py apps/api/tests/test_ledger_calculations.py
git commit -m "feat(api): add ledger payout calculations"
```

---

### Task 2: Backend Ledger Models And SQLite Store

**Files:**

- Create: `apps/api/app/domain/ledger/models.py`
- Create: `apps/api/app/storage/ledger_store.py`
- Modify: `apps/api/app/storage/db.py`
- Test: `apps/api/tests/test_ledger_store.py`

- [ ] **Step 1: Write failing store tests**

Create `apps/api/tests/test_ledger_store.py`:

```python
import importlib
import os


def _store(tmp_path):
    os.environ["FC_SQLITE_PATH"] = str(tmp_path / "ledger.sqlite3")
    settings = importlib.import_module("app.settings")
    importlib.reload(settings)
    store_mod = importlib.import_module("app.storage.ledger_store")
    importlib.reload(store_mod)
    return store_mod.LedgerStore()


def _leg(match_id: int = 1, play_type: str = "SPF", selection: str = "胜", sp: float = 1.8):
    return {
        "matchKey": f"2026-05-14 League Home{match_id} vs Away{match_id}",
        "matchId": match_id,
        "league": "League",
        "homeTeam": f"Home{match_id}",
        "awayTeam": f"Away{match_id}",
        "kickoffTime": "2026-05-14T19:00:00",
        "playType": play_type,
        "selection": selection,
        "sp": sp,
        "handicap": None,
    }


def test_create_pending_ticket_round_trips_with_legs(tmp_path):
    store = _store(tmp_path)

    ticket = store.create_ticket(
        date="2026-05-14",
        status="pending",
        pass_type="2x1",
        multiplier=10,
        stake=20.0,
        estimated_payout=63.0,
        actual_payout=0.0,
        profit=0.0,
        legs=[_leg(1, "SPF", "胜", 1.5), _leg(2, "RQSPF", "让胜", 2.1)],
    )

    loaded = store.get_ticket(ticket.id)
    assert loaded is not None
    assert loaded.id == ticket.id
    assert loaded.status == "pending"
    assert loaded.passType == "2x1"
    assert len(loaded.legs) == 2
    assert loaded.legs[1].playType == "RQSPF"


def test_summary_counts_pending_and_settled_tickets(tmp_path):
    store = _store(tmp_path)
    store.create_ticket(
        date="2026-05-14",
        status="pending",
        pass_type="1x1",
        multiplier=10,
        stake=20.0,
        estimated_payout=36.0,
        actual_payout=0.0,
        profit=0.0,
        legs=[_leg(1)],
    )
    settled = store.create_ticket(
        date="2026-05-14",
        status="settled",
        pass_type="1x1",
        multiplier=10,
        stake=20.0,
        estimated_payout=36.0,
        actual_payout=36.0,
        profit=16.0,
        legs=[_leg(2)],
    )
    store.settle_ticket(
        ticket_id=settled.id,
        actual_payout=36.0,
        profit=16.0,
        leg_results=[{"legId": settled.legs[0].id, "resultSelection": "胜", "isHit": True}],
    )

    summary = store.summary(start="2026-05-14", end="2026-05-14")
    assert summary["stake"] == 40.0
    assert summary["payout"] == 36.0
    assert summary["profit"] == 16.0
    assert summary["pendingCount"] == 1
    assert summary["settledCount"] == 1
    assert summary["ticketCount"] == 2
```

- [ ] **Step 2: Run store tests and verify RED**

Run:

```bash
cd apps/api && uv run python -m pytest tests/test_ledger_store.py -q
```

Expected: FAIL because ledger models/store do not exist.

- [ ] **Step 3: Add ledger Pydantic models**

Create `apps/api/app/domain/ledger/models.py`:

```python
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


LedgerStatus = Literal["pending", "settled"]
LedgerMode = Literal["schedule", "results"]
LedgerPlayType = Literal["SPF", "RQSPF"]


class LedgerLegInput(BaseModel):
    matchKey: Annotated[str, Field(min_length=1)]
    matchId: int | None = None
    league: str
    homeTeam: str
    awayTeam: str
    kickoffTime: str | None = None
    playType: LedgerPlayType
    selection: str
    sp: Annotated[float, Field(gt=1.0, le=1000)]
    handicap: float | None = None


class LedgerTicketCreate(BaseModel):
    mode: LedgerMode
    date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    multiplier: Annotated[int, Field(ge=1, le=9999)]
    legs: Annotated[list[LedgerLegInput], Field(min_length=1)]


class LedgerLegOut(LedgerLegInput):
    id: int
    resultSelection: str | None = None
    isHit: bool | None = None


class LedgerTicketOut(BaseModel):
    id: str
    date: str
    status: LedgerStatus
    passType: str
    multiplier: int
    stake: float
    estimatedPayout: float
    actualPayout: float
    profit: float
    createdAt: int
    settledAt: int | None = None
    legs: list[LedgerLegOut]
```

- [ ] **Step 4: Add SQLite migrations**

Modify `apps/api/app/storage/db.py` inside `migrate()` after the existing `tickets` table:

```python
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ledger_tickets (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            pass_type TEXT NOT NULL,
            multiplier INTEGER NOT NULL,
            stake REAL NOT NULL,
            estimated_payout REAL NOT NULL,
            actual_payout REAL NOT NULL,
            profit REAL NOT NULL,
            created_at INTEGER NOT NULL,
            settled_at INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ledger_legs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT NOT NULL,
            match_key TEXT NOT NULL,
            match_id INTEGER,
            league TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            kickoff_time TEXT,
            play_type TEXT NOT NULL,
            selection TEXT NOT NULL,
            sp REAL NOT NULL,
            handicap REAL,
            result_selection TEXT,
            is_hit INTEGER,
            FOREIGN KEY(ticket_id) REFERENCES ledger_tickets(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ledger_tickets_date ON ledger_tickets(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ledger_tickets_status ON ledger_tickets(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ledger_legs_ticket ON ledger_legs(ticket_id)")
```

- [ ] **Step 5: Implement LedgerStore**

Create `apps/api/app/storage/ledger_store.py`:

```python
from __future__ import annotations

import sqlite3
import uuid

from app.domain.ledger.models import LedgerLegInput, LedgerLegOut, LedgerTicketOut
from app.domain.ledger.calculations import round2

from .db import connect, migrate, now_epoch


class LedgerStore:
    def __init__(self) -> None:
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = connect()
            migrate(self._conn)
        return self._conn

    def create_ticket(
        self,
        *,
        date: str,
        status: str,
        pass_type: str,
        multiplier: int,
        stake: float,
        estimated_payout: float,
        actual_payout: float,
        profit: float,
        legs: list[dict] | list[LedgerLegInput],
    ) -> LedgerTicketOut:
        ticket_id = uuid.uuid4().hex
        created_at = now_epoch()
        settled_at = created_at if status == "settled" else None
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO ledger_tickets(id, date, status, pass_type, multiplier, stake, "
            "estimated_payout, actual_payout, profit, created_at, settled_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ticket_id,
                date,
                status,
                pass_type,
                multiplier,
                round2(stake),
                round2(estimated_payout),
                round2(actual_payout),
                round2(profit),
                created_at,
                settled_at,
            ),
        )
        for raw in legs:
            leg = raw if isinstance(raw, LedgerLegInput) else LedgerLegInput.model_validate(raw)
            conn.execute(
                "INSERT INTO ledger_legs(ticket_id, match_key, match_id, league, home_team, "
                "away_team, kickoff_time, play_type, selection, sp, handicap) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ticket_id,
                    leg.matchKey,
                    leg.matchId,
                    leg.league,
                    leg.homeTeam,
                    leg.awayTeam,
                    leg.kickoffTime,
                    leg.playType,
                    leg.selection,
                    leg.sp,
                    leg.handicap,
                ),
            )
        conn.commit()
        loaded = self.get_ticket(ticket_id)
        assert loaded is not None
        return loaded

    def get_ticket(self, ticket_id: str) -> LedgerTicketOut | None:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM ledger_tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return None
        return self._ticket_from_row(row)

    def list_tickets(
        self,
        *,
        start: str | None = None,
        end: str | None = None,
        date: str | None = None,
        status: str = "all",
    ) -> list[LedgerTicketOut]:
        conn = self._get_conn()
        clauses: list[str] = []
        args: list[object] = []
        if date:
            clauses.append("date = ?")
            args.append(date)
        if start:
            clauses.append("date >= ?")
            args.append(start)
        if end:
            clauses.append("date <= ?")
            args.append(end)
        if status != "all":
            clauses.append("status = ?")
            args.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM ledger_tickets {where} ORDER BY created_at DESC",
            args,
        ).fetchall()
        return [self._ticket_from_row(row) for row in rows]

    def pending_tickets(self) -> list[LedgerTicketOut]:
        return self.list_tickets(status="pending")

    def settle_ticket(
        self,
        *,
        ticket_id: str,
        actual_payout: float,
        profit: float,
        leg_results: list[dict],
    ) -> LedgerTicketOut:
        conn = self._get_conn()
        settled_at = now_epoch()
        conn.execute(
            "UPDATE ledger_tickets SET status = 'settled', actual_payout = ?, profit = ?, "
            "settled_at = ? WHERE id = ? AND status = 'pending'",
            (round2(actual_payout), round2(profit), settled_at, ticket_id),
        )
        for item in leg_results:
            conn.execute(
                "UPDATE ledger_legs SET result_selection = ?, is_hit = ? WHERE id = ?",
                (
                    item["resultSelection"],
                    1 if item["isHit"] else 0,
                    item["legId"],
                ),
            )
        conn.commit()
        loaded = self.get_ticket(ticket_id)
        assert loaded is not None
        return loaded

    def summary(self, *, start: str, end: str) -> dict:
        tickets = self.list_tickets(start=start, end=end, status="all")
        return {
            "stake": round2(sum(t.stake for t in tickets)),
            "payout": round2(sum(t.actualPayout for t in tickets if t.status == "settled")),
            "profit": round2(sum(t.profit for t in tickets if t.status == "settled")),
            "pendingCount": sum(1 for t in tickets if t.status == "pending"),
            "settledCount": sum(1 for t in tickets if t.status == "settled"),
            "ticketCount": len(tickets),
        }

    def _ticket_from_row(self, row: sqlite3.Row) -> LedgerTicketOut:
        legs = self._legs_for_ticket(row["id"])
        return LedgerTicketOut(
            id=row["id"],
            date=row["date"],
            status=row["status"],
            passType=row["pass_type"],
            multiplier=int(row["multiplier"]),
            stake=float(row["stake"]),
            estimatedPayout=float(row["estimated_payout"]),
            actualPayout=float(row["actual_payout"]),
            profit=float(row["profit"]),
            createdAt=int(row["created_at"]),
            settledAt=int(row["settled_at"]) if row["settled_at"] else None,
            legs=legs,
        )

    def _legs_for_ticket(self, ticket_id: str) -> list[LedgerLegOut]:
        rows = self._get_conn().execute(
            "SELECT * FROM ledger_legs WHERE ticket_id = ? ORDER BY id",
            (ticket_id,),
        ).fetchall()
        return [
            LedgerLegOut(
                id=int(row["id"]),
                matchKey=row["match_key"],
                matchId=int(row["match_id"]) if row["match_id"] is not None else None,
                league=row["league"],
                homeTeam=row["home_team"],
                awayTeam=row["away_team"],
                kickoffTime=row["kickoff_time"],
                playType=row["play_type"],
                selection=row["selection"],
                sp=float(row["sp"]),
                handicap=float(row["handicap"]) if row["handicap"] is not None else None,
                resultSelection=row["result_selection"],
                isHit=bool(row["is_hit"]) if row["is_hit"] is not None else None,
            )
            for row in rows
        ]
```

- [ ] **Step 6: Run store tests and verify GREEN**

Run:

```bash
cd apps/api && uv run python -m pytest tests/test_ledger_store.py -q
```

Expected: PASS. If local pytest exits `139`, run:

```bash
cd apps/api && uv run python -m compileall app/domain/ledger app/storage/ledger_store.py app/storage/db.py
```

Expected: compile succeeds.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/domain/ledger/models.py apps/api/app/storage/ledger_store.py apps/api/app/storage/db.py apps/api/tests/test_ledger_store.py
git commit -m "feat(api): persist ledger tickets"
```

---

### Task 3: Backend Settlement Logic

**Files:**

- Create: `apps/api/app/domain/ledger/settlement.py`
- Test: `apps/api/tests/test_ledger_settlement.py`

- [ ] **Step 1: Write failing settlement tests**

Create `apps/api/tests/test_ledger_settlement.py`:

```python
from app.domain.ledger.settlement import settle_ticket_if_ready
from app.domain.ledger.models import LedgerTicketOut, LedgerLegOut


def _ticket(legs, estimated=63.0, stake=20.0):
    return LedgerTicketOut(
        id="ticket1",
        date="2026-05-14",
        status="pending",
        passType=f"{len(legs)}x1",
        multiplier=10,
        stake=stake,
        estimatedPayout=estimated,
        actualPayout=0.0,
        profit=0.0,
        createdAt=1,
        settledAt=None,
        legs=legs,
    )


def _leg(idx: int, play_type: str, selection: str):
    return LedgerLegOut(
        id=idx,
        matchKey=f"match-{idx}",
        matchId=idx,
        league="L",
        homeTeam="H",
        awayTeam="A",
        kickoffTime=None,
        playType=play_type,
        selection=selection,
        sp=1.5,
        handicap=None,
        resultSelection=None,
        isHit=None,
    )


def test_settlement_waits_when_any_result_is_missing():
    ticket = _ticket([_leg(1, "SPF", "胜"), _leg(2, "SPF", "平")])

    result = settle_ticket_if_ready(ticket, {"match-1": {"outcomeSPF": "胜"}})

    assert result is None


def test_fixed_nx1_wins_only_when_all_legs_hit():
    ticket = _ticket([_leg(1, "SPF", "胜"), _leg(2, "RQSPF", "让负")], estimated=52.5)

    result = settle_ticket_if_ready(
        ticket,
        {
            "match-1": {"outcomeSPF": "胜"},
            "match-2": {"outcomeRQSPF": "让负"},
        },
    )

    assert result is not None
    assert result.actualPayout == 52.5
    assert result.profit == 32.5
    assert [r["isHit"] for r in result.legResults] == [True, True]


def test_fixed_nx1_loses_when_one_leg_misses():
    ticket = _ticket([_leg(1, "SPF", "胜"), _leg(2, "RQSPF", "让负")], stake=20.0)

    result = settle_ticket_if_ready(
        ticket,
        {
            "match-1": {"outcomeSPF": "胜"},
            "match-2": {"outcomeRQSPF": "让胜"},
        },
    )

    assert result is not None
    assert result.actualPayout == 0.0
    assert result.profit == -20.0
    assert [r["isHit"] for r in result.legResults] == [True, False]
```

- [ ] **Step 2: Run settlement tests and verify RED**

Run:

```bash
cd apps/api && uv run python -m pytest tests/test_ledger_settlement.py -q
```

Expected: FAIL because `settlement.py` does not exist.

- [ ] **Step 3: Implement settlement logic**

Create `apps/api/app/domain/ledger/settlement.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.ledger.calculations import compute_profit
from app.domain.ledger.models import LedgerTicketOut


@dataclass(frozen=True)
class SettlementResult:
    actualPayout: float
    profit: float
    legResults: list[dict]


def _result_for_leg(leg, result: dict[str, Any]) -> str | None:
    if leg.playType == "SPF":
        return result.get("outcomeSPF")
    if leg.playType == "RQSPF":
        return result.get("outcomeRQSPF")
    return None


def settle_ticket_if_ready(
    ticket: LedgerTicketOut,
    results_by_match_key: dict[str, dict[str, Any]],
) -> SettlementResult | None:
    leg_results: list[dict] = []
    all_hit = True

    for leg in ticket.legs:
        result = results_by_match_key.get(leg.matchKey)
        if not result:
            return None
        result_selection = _result_for_leg(leg, result)
        if result_selection is None:
            return None
        is_hit = result_selection == leg.selection
        all_hit = all_hit and is_hit
        leg_results.append(
            {
                "legId": leg.id,
                "resultSelection": result_selection,
                "isHit": is_hit,
            }
        )

    actual_payout = ticket.estimatedPayout if all_hit else 0.0
    return SettlementResult(
        actualPayout=actual_payout,
        profit=compute_profit(actual_payout=actual_payout, stake=ticket.stake),
        legResults=leg_results,
    )
```

- [ ] **Step 4: Run settlement tests and verify GREEN**

Run:

```bash
cd apps/api && uv run python -m pytest tests/test_ledger_settlement.py -q
```

Expected: PASS. If local pytest exits `139`, run:

```bash
cd apps/api && uv run python -m compileall app/domain/ledger/settlement.py
```

Expected: compile succeeds.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/domain/ledger/settlement.py apps/api/tests/test_ledger_settlement.py
git commit -m "feat(api): add ledger settlement logic"
```

---

### Task 4: Ledger API Routes And Settlement Service

**Files:**

- Create: `apps/api/app/routes/ledger.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/domain/results/scheduler.py`
- Test: `apps/api/tests/test_ledger_api.py`

- [ ] **Step 1: Write failing API tests**

Create `apps/api/tests/test_ledger_api.py`:

```python
import importlib
import os


def _client(tmp_path):
    os.environ["FC_SQLITE_PATH"] = str(tmp_path / "api.sqlite3")
    os.environ["FC_RESULTS_PROVIDER"] = "mock"
    os.environ["FC_MATCHES_SCHEDULER_ENABLED"] = "false"
    settings = importlib.import_module("app.settings")
    importlib.reload(settings)
    main = importlib.import_module("app.main")
    importlib.reload(main)
    from fastapi.testclient import TestClient

    return TestClient(main.app)


def _payload(mode="schedule"):
    return {
        "mode": mode,
        "date": "2026-05-14",
        "multiplier": 10,
        "legs": [
            {
                "matchKey": "2026-05-14 EPL A vs B",
                "matchId": 1,
                "league": "EPL",
                "homeTeam": "A",
                "awayTeam": "B",
                "kickoffTime": "2026-05-14T19:00:00",
                "playType": "SPF",
                "selection": "平",
                "sp": 1.5,
                "handicap": None,
            },
            {
                "matchKey": "2026-05-14 EPL C vs D",
                "matchId": 2,
                "league": "EPL",
                "homeTeam": "C",
                "awayTeam": "D",
                "kickoffTime": "2026-05-14T20:00:00",
                "playType": "RQSPF",
                "selection": "让平",
                "sp": 2.0,
                "handicap": None,
            },
        ],
    }


def test_create_schedule_ticket_returns_pending_ticket(tmp_path):
    client = _client(tmp_path)

    resp = client.post("/api/ledger/tickets", json=_payload("schedule"))

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    assert body["passType"] == "2x1"
    assert body["stake"] == 20.0
    assert body["estimatedPayout"] == 60.0


def test_create_results_ticket_settles_immediately_with_mock_results(tmp_path):
    client = _client(tmp_path)

    resp = client.post("/api/ledger/tickets", json=_payload("results"))

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "settled"
    assert body["actualPayout"] == 60.0
    assert body["profit"] == 40.0


def test_summary_and_ticket_list_return_created_tickets(tmp_path):
    client = _client(tmp_path)
    client.post("/api/ledger/tickets", json=_payload("schedule"))

    summary = client.get("/api/ledger/summary?start=2026-05-14&end=2026-05-14").json()
    tickets = client.get("/api/ledger/tickets?date=2026-05-14&status=all").json()

    assert summary["stake"] == 20.0
    assert summary["pendingCount"] == 1
    assert len(tickets) == 1
```

- [ ] **Step 2: Run API tests and verify RED**

Run:

```bash
cd apps/api && uv run python -m pytest tests/test_ledger_api.py -q
```

Expected: FAIL because `/api/ledger/tickets` does not exist.

- [ ] **Step 3: Implement ledger routes**

Create `apps/api/app/routes/ledger.py`:

```python
from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi import APIRouter, HTTPException

from app.domain.ledger.calculations import compute_estimated_payout, compute_profit, compute_stake
from app.domain.ledger.models import LedgerTicketCreate
from app.domain.ledger.settlement import settle_ticket_if_ready
from app.domain.results.factory import get_results_provider
from app.storage.ledger_store import LedgerStore

router = APIRouter(prefix="/api/ledger", tags=["ledger"])
store = LedgerStore()


def _results_for_ticket(ticket) -> dict[str, dict[str, Any]]:
    provider = get_results_provider()
    return provider.get_results_by_match_keys([leg.matchKey for leg in ticket.legs])


def _settle_created_ticket(ticket):
    result = settle_ticket_if_ready(ticket, _results_for_ticket(ticket))
    if result is None:
        return ticket
    return store.settle_ticket(
        ticket_id=ticket.id,
        actual_payout=result.actualPayout,
        profit=result.profit,
        leg_results=result.legResults,
    )


def settle_pending_tickets() -> int:
    settled = 0
    for ticket in store.pending_tickets():
        result = settle_ticket_if_ready(ticket, _results_for_ticket(ticket))
        if result is None:
            continue
        store.settle_ticket(
            ticket_id=ticket.id,
            actual_payout=result.actualPayout,
            profit=result.profit,
            leg_results=result.legResults,
        )
        settled += 1
    return settled


@router.post("/tickets")
def create_ticket(payload: LedgerTicketCreate):
    pass_type = f"{len(payload.legs)}x1"
    stake = compute_stake(multiplier=payload.multiplier)
    estimated = compute_estimated_payout(
        sp_values=[leg.sp for leg in payload.legs],
        multiplier=payload.multiplier,
    )
    ticket = store.create_ticket(
        date=payload.date,
        status="pending",
        pass_type=pass_type,
        multiplier=payload.multiplier,
        stake=stake,
        estimated_payout=estimated,
        actual_payout=0.0,
        profit=0.0,
        legs=payload.legs,
    )
    if payload.mode == "results":
        ticket = _settle_created_ticket(ticket)
    return ticket.model_dump()


@router.post("/settle")
def settle() -> dict[str, int]:
    return {"settledCount": settle_pending_tickets()}


@router.get("/summary")
def summary(start: dt.date, end: dt.date) -> dict:
    settle_pending_tickets()
    return store.summary(start=start.isoformat(), end=end.isoformat())


@router.get("/tickets")
def list_tickets(
    date: dt.date | None = None,
    start: dt.date | None = None,
    end: dt.date | None = None,
    status: str = "all",
) -> list[dict]:
    if status not in {"all", "pending", "settled"}:
        raise HTTPException(status_code=400, detail="invalid status")
    settle_pending_tickets()
    return [
        ticket.model_dump()
        for ticket in store.list_tickets(
            date=date.isoformat() if date else None,
            start=start.isoformat() if start else None,
            end=end.isoformat() if end else None,
            status=status,
        )
    ]


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str) -> dict:
    settle_pending_tickets()
    ticket = store.get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="not found")
    return ticket.model_dump()
```

- [ ] **Step 4: Wire router into FastAPI**

Modify `apps/api/app/main.py`:

```python
from app.routes.ledger import router as ledger_router
```

Then include it after existing routers:

```python
app.include_router(ledger_router)
```

- [ ] **Step 5: Call settlement after match scheduler refresh**

Modify `apps/api/app/domain/results/scheduler.py` after each `_refresh_once(...)` call:

```python
        try:
            from app.routes.ledger import settle_pending_tickets

            await asyncio.to_thread(settle_pending_tickets)
        except Exception:
            logger.exception("failed to settle pending ledger tickets")
```

- [ ] **Step 6: Run API tests and verify GREEN**

Run:

```bash
cd apps/api && uv run python -m pytest tests/test_ledger_api.py -q
```

Expected: PASS. If local pytest exits `139`, run:

```bash
cd apps/api && uv run python -m compileall app/routes/ledger.py app/main.py app/domain/results/scheduler.py
curl -s -X POST http://127.0.0.1:8000/api/ledger/tickets \
  -H 'Content-Type: application/json' \
  -d '{"mode":"schedule","date":"2026-05-14","multiplier":10,"legs":[{"matchKey":"2026-05-14 EPL A vs B","matchId":1,"league":"EPL","homeTeam":"A","awayTeam":"B","kickoffTime":"2026-05-14T19:00:00","playType":"SPF","selection":"平","sp":1.5,"handicap":null}]}'
```

Expected: compile succeeds and curl returns a JSON ticket.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/routes/ledger.py apps/api/app/main.py apps/api/app/domain/results/scheduler.py apps/api/tests/test_ledger_api.py
git commit -m "feat(api): add ledger ticket endpoints"
```

---

### Task 5: Frontend Ledger API Client And Math Helper

**Files:**

- Modify: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/lib/ledgerMath.ts`

- [ ] **Step 1: Add frontend ledger types and API client**

Modify `apps/web/src/lib/api.ts` by adding:

```ts
export type LedgerStatus = "pending" | "settled";
export type LedgerMode = "schedule" | "results";

export type LedgerLegInput = {
  matchKey: string;
  matchId?: number | null;
  league: string;
  homeTeam: string;
  awayTeam: string;
  kickoffTime?: string | null;
  playType: TicketPlayType;
  selection: string;
  sp: number;
  handicap?: number | null;
};

export type LedgerLeg = LedgerLegInput & {
  id: number;
  resultSelection?: string | null;
  isHit?: boolean | null;
};

export type LedgerTicket = {
  id: string;
  date: string;
  status: LedgerStatus;
  passType: string;
  multiplier: number;
  stake: number;
  estimatedPayout: number;
  actualPayout: number;
  profit: number;
  createdAt: number;
  settledAt?: number | null;
  legs: LedgerLeg[];
};

export type LedgerSummary = {
  stake: number;
  payout: number;
  profit: number;
  pendingCount: number;
  settledCount: number;
  ticketCount: number;
};

export async function createLedgerTicket(input: {
  mode: LedgerMode;
  date: string;
  multiplier: number;
  legs: LedgerLegInput[];
}): Promise<LedgerTicket> {
  return await apiFetch<LedgerTicket>("/api/ledger/tickets", {
    method: "POST",
    json: input,
  });
}

export async function settleLedgerTickets(): Promise<{ settledCount: number }> {
  return await apiFetch<{ settledCount: number }>("/api/ledger/settle", {
    method: "POST",
  });
}

export async function getLedgerSummary(start: string, end: string): Promise<LedgerSummary> {
  return await apiFetch<LedgerSummary>(
    `/api/ledger/summary?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
  );
}

export async function listLedgerTickets(input: {
  date?: string;
  start?: string;
  end?: string;
  status?: "all" | "pending" | "settled";
}): Promise<LedgerTicket[]> {
  const params = new URLSearchParams();
  if (input.date) params.set("date", input.date);
  if (input.start) params.set("start", input.start);
  if (input.end) params.set("end", input.end);
  params.set("status", input.status ?? "all");
  return await apiFetch<LedgerTicket[]>(`/api/ledger/tickets?${params.toString()}`);
}

export async function getLedgerTicket(id: string): Promise<LedgerTicket> {
  return await apiFetch<LedgerTicket>(`/api/ledger/tickets/${encodeURIComponent(id)}`);
}
```

- [ ] **Step 2: Add frontend display math helper**

Create `apps/web/src/lib/ledgerMath.ts`:

```ts
export function round2(n: number) {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

export function computeStake(multiplier: number) {
  return round2(2 * multiplier);
}

export function computeEstimatedPayout(spValues: number[], multiplier: number) {
  const product = spValues.reduce((acc, sp) => acc * sp, 1);
  return round2(2 * multiplier * product);
}
```

- [ ] **Step 3: Verify TypeScript build**

Run:

```bash
cd apps/web && npm run build
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/lib/api.ts apps/web/src/lib/ledgerMath.ts
git commit -m "feat(web): add ledger api client"
```

---

### Task 6: Selectable Odds And Confirmation Sheet On Matches Page

**Files:**

- Modify: `apps/web/src/app/wanzhan/matches/page.tsx`

- [ ] **Step 1: Add selection types/helpers near page types**

Add:

```ts
type SelectedLeg = {
  matchKey: string;
  matchId?: number | null;
  league: string;
  homeTeam: string;
  awayTeam: string;
  kickoffTime?: string | null;
  playType: "SPF" | "RQSPF";
  selection: string;
  sp: number;
  handicap?: number | null;
};

function parseOdd(value: string | undefined | null): number | null {
  if (!value) return null;
  const n = Number(value);
  return Number.isFinite(n) && n > 1 ? n : null;
}

function selectedKey(matchKey: string) {
  return matchKey;
}
```

- [ ] **Step 2: Add state inside `WanzhanMatchesPage`**

Add:

```ts
const [selected, setSelected] = useState<Record<string, SelectedLeg>>({});
const [ticketOpen, setTicketOpen] = useState(false);
const [multiplier, setMultiplier] = useState(1);
const [submitting, setSubmitting] = useState(false);
const selectedLegs = useMemo(() => Object.values(selected), [selected]);
const ticketMode = view === "results" ? "results" : "schedule";
```

- [ ] **Step 3: Add toggle helper**

Inside the component add:

```ts
function toggleLeg(match: MatchItem, leg: Omit<SelectedLeg, "matchKey" | "matchId" | "league" | "homeTeam" | "awayTeam" | "kickoffTime">) {
  const key = selectedKey(match.matchKey);
  setSelected((prev) => {
    const current = prev[key];
    if (
      current &&
      current.playType === leg.playType &&
      current.selection === leg.selection
    ) {
      const next = { ...prev };
      delete next[key];
      return next;
    }
    return {
      ...prev,
      [key]: {
        matchKey: match.matchKey,
        matchId: match.matchId ?? null,
        league: match.league,
        homeTeam: match.homeTeam,
        awayTeam: match.awayTeam,
        kickoffTime: match.kickoffTime,
        ...leg,
      },
    };
  });
}
```

- [ ] **Step 4: Replace read-only odds grid with clickable buttons**

Replace `oddsGrid(...)` use with a local render block that calls `toggleLeg(...)`. Each option button:

```tsx
const active = selected[m.matchKey]?.playType === "SPF" && selected[m.matchKey]?.selection === "胜";
const sp = parseOdd(m.had?.h);
<button
  type="button"
  disabled={sp == null}
  onClick={() => sp && toggleLeg(m, { playType: "SPF", selection: "胜", sp, handicap: null })}
  style={{
    border: active ? "1px solid #222" : "1px solid #ddd",
    background: active ? "#222" : "#fff",
    color: active ? "#fff" : "#111",
    borderRadius: 10,
    padding: "9px 8px",
    fontWeight: 750,
  }}
>
  主胜<br />
  <span style={{ fontSize: 12, color: active ? "#fff" : "#666" }}>{m.had?.h ?? "-"}</span>
</button>
```

Repeat for:

- SPF `平`: `m.had?.d`, selection `平`
- SPF `客胜`: `m.had?.a`, selection `负`
- RQSPF `让胜`: `m.hhad?.h`, selection `让胜`, handicap from `m.hhad?.goalLine`
- RQSPF `让平`: `m.hhad?.d`, selection `让平`
- RQSPF `让负`: `m.hhad?.a`, selection `让负`

- [ ] **Step 5: Add floating ticket button**

Before closing `</WanzhanShell>`, render:

```tsx
{selectedLegs.length > 0 ? (
  <button
    type="button"
    onClick={() => setTicketOpen(true)}
    style={{
      position: "fixed",
      right: 18,
      bottom: 82,
      zIndex: 20,
      border: "1px solid #222",
      background: "#222",
      color: "#fff",
      borderRadius: 999,
      padding: "14px 18px",
      fontSize: 15,
      fontWeight: 900,
      boxShadow: "0 10px 24px rgba(0,0,0,.18)",
    }}
  >
    {ticketMode === "results" ? "补记" : "出票"} · {selectedLegs.length}场
  </button>
) : null}
```

- [ ] **Step 6: Add confirmation sheet**

Render fixed overlay when `ticketOpen` is true. Use `computeStake`, `computeEstimatedPayout`, and `createLedgerTicket`:

```tsx
const stake = computeStake(multiplier);
const estimatedPayout = computeEstimatedPayout(selectedLegs.map((l) => l.sp), multiplier);
```

On submit:

```ts
setSubmitting(true);
try {
  await createLedgerTicket({
    mode: ticketMode,
    date: today,
    multiplier,
    legs: selectedLegs,
  });
  setSelected({});
  setTicketOpen(false);
  setMultiplier(1);
  if (view === "schedule") void loadSchedule();
  else void loadResultsWeek();
} catch (e) {
  setError(e instanceof Error ? e.message : String(e));
} finally {
  setSubmitting(false);
}
```

- [ ] **Step 7: Verify frontend build**

Run:

```bash
cd apps/web && npm run build
```

Expected: build succeeds.

- [ ] **Step 8: Manual browser verification**

Open:

```text
http://localhost:3000/wanzhan/matches
```

Verify:

- Selecting SPF then RQSPF on same match replaces selection.
- Re-clicking same selected option clears it.
- Floating button appears with correct count.
- Multiplier changes stake and estimated payout.
- Schedule mode submit creates pending ticket.
- Results mode submit creates settled ticket when results exist.

- [ ] **Step 9: Commit**

```bash
git add apps/web/src/app/wanzhan/matches/page.tsx
git commit -m "feat(web): add match odds ticketing"
```

---

### Task 7: Backend-Backed Ledger Pages

**Files:**

- Modify: `apps/web/src/app/wanzhan/ledger/page.tsx`
- Modify: `apps/web/src/app/wanzhan/ledger/day/[date]/page.tsx`
- Create: `apps/web/src/app/wanzhan/ledger/tickets/[id]/page.tsx`
- Modify: `apps/web/src/app/wanzhan/matches/page.tsx`

- [ ] **Step 1: Replace ledger summary on main ledger page**

In `apps/web/src/app/wanzhan/ledger/page.tsx`, replace `summarizeDay`, `summarizePeriod`, and `listTicketsByDate` imports with:

```ts
import { getLedgerSummary, listLedgerTickets, type LedgerSummary, type LedgerTicket } from "../../../lib/api";
```

Add state/effect:

```ts
const [summary, setSummary] = useState<LedgerSummary | null>(null);
const [tickets, setTickets] = useState<LedgerTicket[]>([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);

useEffect(() => {
  let cancelled = false;
  (async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextSummary, nextTickets] = await Promise.all([
        getLedgerSummary(range.start, range.end),
        listLedgerTickets({ date, status: "all" }),
      ]);
      if (cancelled) return;
      setSummary(nextSummary);
      setTickets(nextTickets);
    } catch (e) {
      if (!cancelled) setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (!cancelled) setLoading(false);
    }
  })();
  return () => {
    cancelled = true;
  };
}, [date, range.end, range.start]);
```

Use fallback values:

```ts
const displaySummary = summary ?? {
  stake: 0,
  payout: 0,
  profit: 0,
  pendingCount: 0,
  settledCount: 0,
  ticketCount: 0,
};
```

- [ ] **Step 2: Update ticket links**

Change ticket card links from `/tickets/${id}/report` to:

```tsx
href={`/wanzhan/ledger/tickets/${encodeURIComponent(t.id)}`}
```

- [ ] **Step 3: Replace day page data source**

In `apps/web/src/app/wanzhan/ledger/day/[date]/page.tsx`, load:

```ts
const [summary, setSummary] = useState<LedgerSummary | null>(null);
const [list, setList] = useState<LedgerTicket[]>([]);
```

Use:

```ts
const [nextSummary, nextList] = await Promise.all([
  getLedgerSummary(date, date),
  listLedgerTickets({ date, status: filter }),
]);
```

Render `estimatedPayout` for pending tickets and `actualPayout/profit` for settled tickets.

- [ ] **Step 4: Add ledger ticket detail page**

Create `apps/web/src/app/wanzhan/ledger/tickets/[id]/page.tsx`:

```tsx
"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { WanzhanShell } from "../../../../../components/wanzhan/WanzhanShell";
import { getLedgerTicket, type LedgerTicket } from "../../../../../lib/api";

function cardStyle() {
  return { background: "#fff", border: "1px solid #eee", borderRadius: 14, padding: 12 } as const;
}

export default function LedgerTicketDetailPage() {
  const params = useParams<{ id: string }>();
  const [ticket, setTicket] = useState<LedgerTicket | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const next = await getLedgerTicket(params.id);
        if (!cancelled) setTicket(next);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  return (
    <WanzhanShell title="票据详情" back>
      {error ? <div style={cardStyle()}>{error}</div> : null}
      {!ticket ? <div style={{ color: "#666", fontSize: 14 }}>加载中...</div> : null}
      {ticket ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={cardStyle()}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <strong>{ticket.passType} · {ticket.multiplier}倍</strong>
              <span>{ticket.status === "pending" ? "待结" : ticket.actualPayout > 0 ? "已中奖" : "未中奖"}</span>
            </div>
            <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
              <div>投入<br /><b>{ticket.stake.toFixed(2)}</b></div>
              <div>回报<br /><b>{ticket.actualPayout.toFixed(2)}</b></div>
              <div>盈亏<br /><b>{ticket.profit.toFixed(2)}</b></div>
            </div>
          </div>
          {ticket.legs.map((leg) => (
            <div key={leg.id} style={cardStyle()}>
              <strong>{leg.homeTeam} vs {leg.awayTeam}</strong>
              <div style={{ marginTop: 6, color: "#666", fontSize: 13 }}>
                {leg.playType} · {leg.selection} @ {leg.sp}
              </div>
              <div style={{ marginTop: 6, color: "#666", fontSize: 13 }}>
                赛果：{leg.resultSelection ?? "待定"} · {leg.isHit == null ? "未结" : leg.isHit ? "命中" : "未中"}
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </WanzhanShell>
  );
}
```

- [ ] **Step 5: Update Wanzhan matches `StatStrip` to use backend summary**

In `apps/web/src/app/wanzhan/matches/page.tsx`, replace `summarizeDay(today)` with `getLedgerSummary(today, today)` plus a separate all-pending query or use summary pending count for today. For the first implementation, display today's pending count from summary and add a comment:

```tsx
// Current API summary is date-range scoped. A later enhancement can add all-pending count.
```

- [ ] **Step 6: Verify frontend build**

Run:

```bash
cd apps/web && npm run build
```

Expected: build succeeds.

- [ ] **Step 7: Manual browser verification**

Verify:

- Ledger page loads backend summary.
- Day page filters pending/settled tickets.
- Ticket cards link to `/wanzhan/ledger/tickets/{id}`.
- Detail page shows leg hit/miss information.

- [ ] **Step 8: Commit**

```bash
git add apps/web/src/app/wanzhan/ledger/page.tsx apps/web/src/app/wanzhan/ledger/day/[date]/page.tsx apps/web/src/app/wanzhan/ledger/tickets/[id]/page.tsx apps/web/src/app/wanzhan/matches/page.tsx
git commit -m "feat(web): read ledger from backend"
```

---

### Task 8: Full Verification And Cleanup

**Files:**

- Modify as needed based on verification findings.

- [ ] **Step 1: Run backend targeted checks**

Run:

```bash
cd apps/api && uv run ruff check app/domain/ledger app/storage/ledger_store.py app/routes/ledger.py tests/test_ledger_*.py
cd apps/api && uv run python -m compileall app/domain/ledger app/storage/ledger_store.py app/routes/ledger.py
```

Expected: ruff and compile pass.

- [ ] **Step 2: Run frontend build**

Run:

```bash
cd apps/web && npm run build
```

Expected: build succeeds.

- [ ] **Step 3: Verify end-to-end manually**

Start services if needed:

```bash
cd apps/api && uv run python -m uvicorn app.main:app --reload --port 8000
cd apps/web && npm run dev
```

In browser:

1. Open `/wanzhan/matches`.
2. Select two schedule-mode odds.
3. Click `出票 · 2场`.
4. Set multiplier `10`.
5. Confirm ticket.
6. Open `/wanzhan/ledger`.
7. Confirm pending count increased.
8. Switch to results mode.
9. Select finished-match odds.
10. Click `补记 · N场`.
11. Confirm ticket.
12. Confirm ledger profit updates immediately.

- [ ] **Step 4: Remove or deprecate old localStorage ledger usage**

If `apps/web/src/lib/wanzhanLedger.ts` is no longer imported, either delete it or leave it unused. Prefer deleting only if no imports remain:

```bash
rg "wanzhanLedger" apps/web/src
```

Expected: no imports. If no imports, delete:

```bash
git rm apps/web/src/lib/wanzhanLedger.ts
```

- [ ] **Step 5: Final commit**

```bash
git add apps/api apps/web
git commit -m "chore: verify ledger ticketing flow"
```

