# Football Calculator MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web MVP that lets users upload football betting ticket photos/screenshots, OCR + parse into an editable structured ticket (including printed SP), fetch match results, and compute estimated payout for SPF/RQSPF with common pass types + multiplier; plus a minimal schedule/results page.

**Architecture:** A small monorepo under `足球计算器/` with a Next.js frontend and a FastAPI backend. Backend owns OCR, parsing, results provider abstraction, and payout engine. Frontend provides upload, correction UI, and report view. Anonymous persistence uses SQLite (upgradeable later).

**Tech Stack:** Next.js (React, TypeScript), FastAPI (Python), Pydantic v2, SQLite, PaddleOCR (Python), pytest, Playwright (optional smoke), Docker optional.

---

## Scope check (decomposition)

The spec includes two subsystems: (1) ticket recognition + payout calculation (core) and (2) football info pages (schedule/results + odds/trends). This plan implements the **core end-to-end flow** and a **minimal schedule/results page** only. A follow-up plan should cover “odds trends + analysis cards” once a data source is chosen.

## Target file structure (lock boundaries)

### Repo layout (inside `足球计算器/`)
- Create: `apps/web/` (Next.js frontend)
- Create: `apps/api/` (FastAPI backend)
- Create: `packages/shared/` (shared JSON schemas + TS types, generated from JSON schema)
- Create: `infra/` (optional docker compose / dev scripts)
- Create: `docs/` (already exists)

### Backend (`apps/api/`)
- Create: `apps/api/pyproject.toml` (deps + tooling)
- Create: `apps/api/app/main.py` (FastAPI app wiring)
- Create: `apps/api/app/settings.py` (env config)
- Create: `apps/api/app/routes/tickets.py` (recognize/validate/calculate)
- Create: `apps/api/app/routes/matches.py` (schedule/results minimal)
- Create: `apps/api/app/domain/tickets/models.py` (Pydantic models for Ticket/TicketDraft/Report)
- Create: `apps/api/app/domain/tickets/validate.py` (validation rules)
- Create: `apps/api/app/domain/tickets/payout.py` (payout engine SPF/RQSPF + pass combos)
- Create: `apps/api/app/domain/tickets/pass_types.py` (combo generation)
- Create: `apps/api/app/domain/ocr/ocr_service.py` (OCR abstraction)
- Create: `apps/api/app/domain/ocr/paddleocr_impl.py` (PaddleOCR implementation)
- Create: `apps/api/app/domain/parser/ticket_parser.py` (parsing pipeline)
- Create: `apps/api/app/domain/parser/fields.py` (regex/dictionaries)
- Create: `apps/api/app/domain/results/provider.py` (ResultsProvider interface)
- Create: `apps/api/app/domain/results/mock_provider.py` (MVP mock/fallback provider)
- Create: `apps/api/app/storage/db.py` (SQLite connection)
- Create: `apps/api/app/storage/anonymous_store.py` (anonToken persistence)
- Create: `apps/api/tests/...` (pytest unit tests)

### Frontend (`apps/web/`)
- Create: `apps/web/package.json`
- Create: `apps/web/src/app/` (Next.js app router)
- Create: `apps/web/src/app/page.tsx` (home)
- Create: `apps/web/src/app/upload/page.tsx`
- Create: `apps/web/src/app/tickets/[id]/edit/page.tsx` (correction UI)
- Create: `apps/web/src/app/tickets/[id]/report/page.tsx`
- Create: `apps/web/src/app/matches/page.tsx` (schedule/results list)
- Create: `apps/web/src/lib/api.ts` (API client)
- Create: `apps/web/src/lib/anonToken.ts` (token storage)
- Create: `apps/web/src/components/TicketEditor.tsx`
- Create: `apps/web/src/components/ImageUpload.tsx`

### Shared (`packages/shared/`)
- Create: `packages/shared/schema/ticket.schema.json`
- Create: `packages/shared/schema/report.schema.json`
- Create: `packages/shared/ts/` (generated types)

## Local dev commands (target)

- API:
  - Run: `cd apps/api && uv run uvicorn app.main:app --reload --port 8000`
  - Test: `cd apps/api && uv run pytest -q`
- Web:
  - Run: `cd apps/web && npm run dev`

---

### Task 1: Bootstrap repo structure (api + web + shared)

**Files:**
- Create: `足球计算器/apps/api/pyproject.toml`
- Create: `足球计算器/apps/api/app/main.py`
- Create: `足球计算器/apps/api/app/settings.py`
- Create: `足球计算器/apps/api/tests/test_health.py`
- Create: `足球计算器/apps/web/package.json`
- Create: `足球计算器/apps/web/src/app/page.tsx`
- Create: `足球计算器/apps/web/src/lib/api.ts`

- [ ] **Step 1: Create backend `pyproject.toml`**

```toml
[project]
name = "football-calculator-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.32.0",
  "pydantic>=2.7.0",
  "pydantic-settings>=2.3.0",
  "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
  "httpx>=0.27.0",
  "ruff>=0.5.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
```

- [ ] **Step 2: Add API settings**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FC_", env_file=".env", extra="ignore")
    sqlite_path: str = "data/app.sqlite3"


settings = Settings()
```

- [ ] **Step 3: Add FastAPI app with health endpoint**

```python
from fastapi import FastAPI

app = FastAPI(title="Football Calculator API", version="0.1.0")


@app.get("/health")
def health():
    return {"ok": True}
```

- [ ] **Step 4: Write failing test first (health)**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_ok():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
```

- [ ] **Step 5: Run tests**

Run: `cd apps/api && uv run pytest -q`  
Expected: PASS

- [ ] **Step 6: Bootstrap minimal web app**

`apps/web/package.json` (minimal):

```json
{
  "name": "football-calculator-web",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000"
  },
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  }
}
```

`apps/web/src/app/page.tsx`:

```tsx
export default function HomePage() {
  return (
    <main style={{ padding: 24, fontFamily: "system-ui" }}>
      <h1>足球计算器</h1>
      <p>上传彩票 → 识别校对 → 计算奖金（MVP）</p>
    </main>
  );
}
```

- [ ] **Step 7: Commit**

```bash
git add 足球计算器/apps/api 足球计算器/apps/web
git commit -m "chore: bootstrap api and web apps"
```

---

### Task 2: Define shared Ticket/Report schemas (single source of truth)

**Files:**
- Create: `足球计算器/packages/shared/schema/ticket.schema.json`
- Create: `足球计算器/packages/shared/schema/report.schema.json`
- Create: `足球计算器/apps/api/app/domain/tickets/models.py`
- Test: `足球计算器/apps/api/tests/test_models_roundtrip.py`

- [ ] **Step 1: Write Ticket JSON schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://football-calculator.local/schema/ticket.json",
  "title": "Ticket",
  "type": "object",
  "required": ["ticketType", "playType", "multiplier", "passTypes", "legs"],
  "properties": {
    "ticketType": { "const": "jc-football" },
    "playType": { "enum": ["SPF", "RQSPF"] },
    "multiplier": { "type": "integer", "minimum": 1, "maximum": 9999 },
    "passTypes": {
      "type": "array",
      "items": { "type": "string", "pattern": "^[2-9]\\dx1$|^\\d+x1$|^[2-9]x1$" },
      "minItems": 1
    },
    "legs": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["matchKey", "selection", "sp"],
        "properties": {
          "matchKey": { "type": "string", "minLength": 1 },
          "selection": { "type": "string" },
          "handicap": { "type": ["number", "null"] },
          "sp": { "type": "number", "exclusiveMinimum": 1.0, "maximum": 1000 }
        }
      }
    }
  }
}
```

- [ ] **Step 2: Write Report schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://football-calculator.local/schema/report.json",
  "title": "PayoutReport",
  "type": "object",
  "required": ["status", "totalPayout", "details", "unmatchedLegs"],
  "properties": {
    "status": { "enum": ["won", "lost", "pending", "partial"] },
    "totalPayout": { "type": "number", "minimum": 0 },
    "details": { "type": "object" },
    "unmatchedLegs": { "type": "array", "items": { "type": "string" } }
  }
}
```

- [ ] **Step 3: Implement Pydantic models matching schema**

```python
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class PlayType(str, Enum):
    SPF = "SPF"
    RQSPF = "RQSPF"


class Leg(BaseModel):
    matchKey: str = Field(min_length=1)
    selection: str
    handicap: float | None = None
    sp: float = Field(gt=1.0, le=1000)


class Ticket(BaseModel):
    ticketType: Literal["jc-football"] = "jc-football"
    playType: PlayType
    multiplier: int = Field(ge=1, le=9999)
    passTypes: list[str] = Field(min_length=1)
    legs: list[Leg] = Field(min_length=1)


class PayoutStatus(str, Enum):
    WON = "won"
    LOST = "lost"
    PENDING = "pending"
    PARTIAL = "partial"


class PayoutReport(BaseModel):
    status: PayoutStatus
    totalPayout: float = Field(ge=0)
    details: dict
    unmatchedLegs: list[str]
```

- [ ] **Step 4: Write model roundtrip test**

```python
from app.domain.tickets.models import Ticket


def test_ticket_roundtrip():
    t = Ticket(
        playType="SPF",
        multiplier=2,
        passTypes=["2x1"],
        legs=[{"matchKey": "2026-05-08 EPL A vs B", "selection": "胜", "sp": 1.85}],
    )
    dumped = t.model_dump()
    loaded = Ticket.model_validate(dumped)
    assert loaded == t
```

- [ ] **Step 5: Run tests**

Run: `cd apps/api && uv run pytest -q`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add 足球计算器/packages/shared 足球计算器/apps/api/app/domain/tickets/models.py 足球计算器/apps/api/tests/test_models_roundtrip.py
git commit -m "feat: define ticket and payout report models"
```

---

### Task 3: Ticket validation rules (blocking calculate until valid)

**Files:**
- Create: `足球计算器/apps/api/app/domain/tickets/validate.py`
- Modify: `足球计算器/apps/api/app/domain/tickets/models.py`
- Test: `足球计算器/apps/api/tests/test_ticket_validation.py`

- [ ] **Step 1: Write failing tests for validation**

```python
import pytest

from app.domain.tickets.models import Ticket
from app.domain.tickets.validate import validate_ticket, TicketValidationError


def test_requires_pass_types():
    t = Ticket(
        playType="SPF",
        multiplier=1,
        passTypes=["2x1"],
        legs=[
            {"matchKey": "m1", "selection": "胜", "sp": 1.6},
            {"matchKey": "m2", "selection": "平", "sp": 3.2},
        ],
    )
    validate_ticket(t)  # no exception


@pytest.mark.parametrize("bad_sp", [0.0, 1.0, -1.0])
def test_rejects_bad_sp(bad_sp: float):
    t = Ticket(
        playType="SPF",
        multiplier=1,
        passTypes=["2x1"],
        legs=[
            {"matchKey": "m1", "selection": "胜", "sp": bad_sp},
            {"matchKey": "m2", "selection": "平", "sp": 3.2},
        ],
    )
    with pytest.raises(TicketValidationError):
        validate_ticket(t)


def test_pass_type_must_match_leg_count():
    t = Ticket(
        playType="SPF",
        multiplier=1,
        passTypes=["3x1"],
        legs=[
            {"matchKey": "m1", "selection": "胜", "sp": 1.6},
            {"matchKey": "m2", "selection": "平", "sp": 3.2},
        ],
    )
    with pytest.raises(TicketValidationError):
        validate_ticket(t)
```

- [ ] **Step 2: Implement validation**

```python
from dataclasses import dataclass

from app.domain.tickets.models import Ticket


@dataclass(frozen=True)
class TicketValidationError(Exception):
    message: str


def _required_legs_for_pass_type(pass_type: str) -> int:
    # "2x1" -> 2
    left, _ = pass_type.split("x", 1)
    return int(left)


def validate_ticket(ticket: Ticket) -> None:
    if not ticket.passTypes:
        raise TicketValidationError("passTypes is required")

    required = max(_required_legs_for_pass_type(p) for p in ticket.passTypes)
    if len(ticket.legs) < required:
        raise TicketValidationError(f"legs must be >= {required} for passTypes={ticket.passTypes}")

    if ticket.playType == "RQSPF":
        for leg in ticket.legs:
            if leg.handicap is None:
                raise TicketValidationError("handicap is required for RQSPF")
```

- [ ] **Step 3: Run tests**

Run: `cd apps/api && uv run pytest -q`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add 足球计算器/apps/api/app/domain/tickets/validate.py 足球计算器/apps/api/tests/test_ticket_validation.py
git commit -m "feat: add ticket validation for MVP calculate gate"
```

---

### Task 4: Pass type combo generation + payout engine (SPF only first, then RQSPF)

**Files:**
- Create: `足球计算器/apps/api/app/domain/tickets/pass_types.py`
- Create: `足球计算器/apps/api/app/domain/tickets/payout.py`
- Test: `足球计算器/apps/api/tests/test_payout_spf.py`
- Test: `足球计算器/apps/api/tests/test_payout_rqspf.py`

- [ ] **Step 1: Write failing tests for SPF payout**

```python
from app.domain.tickets.models import Ticket
from app.domain.tickets.payout import compute_payout


def test_spf_two_legs_2x1_wins():
    ticket = Ticket(
        playType="SPF",
        multiplier=2,
        passTypes=["2x1"],
        legs=[
            {"matchKey": "m1", "selection": "胜", "sp": 1.5},
            {"matchKey": "m2", "selection": "负", "sp": 2.0},
        ],
    )
    results = {"m1": {"outcomeSPF": "胜"}, "m2": {"outcomeSPF": "负"}}
    report = compute_payout(ticket, results)
    # (1.5 * 2.0) * 2元 * multiplier(2) = 12.0
    assert report.status == "won"
    assert report.totalPayout == 12.0
```

- [ ] **Step 2: Implement combo generation for Nx1**

```python
import itertools


def combos(leg_indexes: list[int], pick: int) -> list[tuple[int, ...]]:
    return list(itertools.combinations(leg_indexes, pick))
```

- [ ] **Step 3: Implement `compute_payout` (SPF)**

```python
from __future__ import annotations

from app.domain.tickets.models import PayoutReport, Ticket
from app.domain.tickets.pass_types import combos


def compute_payout(ticket: Ticket, results_by_match_key: dict) -> PayoutReport:
    unmatched = []
    leg_hits: list[bool] = []
    for leg in ticket.legs:
        res = results_by_match_key.get(leg.matchKey)
        if not res:
            unmatched.append(leg.matchKey)
            leg_hits.append(False)
            continue
        if ticket.playType == "SPF":
            leg_hits.append(res["outcomeSPF"] == leg.selection)
        else:
            leg_hits.append(res["outcomeRQSPF"] == leg.selection)

    if unmatched:
        return PayoutReport(status="partial", totalPayout=0.0, details={"legHits": leg_hits}, unmatchedLegs=unmatched)

    total = 0.0
    idxs = list(range(len(ticket.legs)))
    for pt in ticket.passTypes:
        pick = int(pt.split("x", 1)[0])
        for c in combos(idxs, pick):
            if all(leg_hits[i] for i in c):
                sp_prod = 1.0
                for i in c:
                    sp_prod *= ticket.legs[i].sp
                total += sp_prod * 2.0 * ticket.multiplier

    status = "won" if total > 0 else "lost"
    return PayoutReport(status=status, totalPayout=round(total, 2), details={"legHits": leg_hits}, unmatchedLegs=[])
```

- [ ] **Step 4: Run tests**

Run: `cd apps/api && uv run pytest -q`  
Expected: PASS

- [ ] **Step 5: Add RQSPF tests + minimal rule**

`test_payout_rqspf.py`:

```python
from app.domain.tickets.models import Ticket
from app.domain.tickets.payout import compute_payout


def test_rqspf_uses_outcome_rqspf():
    ticket = Ticket(
        playType="RQSPF",
        multiplier=1,
        passTypes=["2x1"],
        legs=[
            {"matchKey": "m1", "selection": "让胜", "handicap": -1, "sp": 2.1},
            {"matchKey": "m2", "selection": "让负", "handicap": +1, "sp": 1.7},
        ],
    )
    results = {"m1": {"outcomeRQSPF": "让胜"}, "m2": {"outcomeRQSPF": "让负"}}
    report = compute_payout(ticket, results)
    assert report.status == "won"
```

- [ ] **Step 6: Run tests**

Run: `cd apps/api && uv run pytest -q`  
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add 足球计算器/apps/api/app/domain/tickets/pass_types.py 足球计算器/apps/api/app/domain/tickets/payout.py 足球计算器/apps/api/tests/test_payout_*.py
git commit -m "feat: add MVP payout engine for SPF/RQSPF with Nx1 pass types"
```

---

### Task 5: OCR abstraction + stub parser (return a deterministic TicketDraft)

**Files:**
- Create: `足球计算器/apps/api/app/domain/ocr/ocr_service.py`
- Create: `足球计算器/apps/api/app/domain/parser/ticket_parser.py`
- Create: `足球计算器/apps/api/app/domain/parser/fields.py`
- Modify: `足球计算器/apps/api/app/domain/tickets/models.py`
- Test: `足球计算器/apps/api/tests/test_recognize_stub.py`

- [ ] **Step 1: Extend models for TicketDraft**

```python
class TicketDraft(BaseModel):
    ticket: Ticket
    confidence: dict
    warnings: list[str]
    sourceImages: list[str]
```

- [ ] **Step 2: Write failing test for recognize stub**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_recognize_returns_ticket_draft():
    client = TestClient(app)
    files = {"images": ("ticket.png", b"fake", "image/png")}
    resp = client.post("/api/tickets/recognize", files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticket"]["ticketType"] == "jc-football"
    assert "warnings" in body
```

- [ ] **Step 3: Implement OCRService interface**

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OcrLine:
    text: str
    confidence: float
    bbox: list[float]


class OcrService:
    def recognize(self, image_bytes: bytes) -> list[OcrLine]:
        raise NotImplementedError()


class StubOcrService(OcrService):
    def recognize(self, image_bytes: bytes) -> list[OcrLine]:
        return [
            OcrLine(text="2串1 倍投2", confidence=0.9, bbox=[0, 0, 1, 1]),
            OcrLine(text="主队A vs 客队B 胜 1.85", confidence=0.9, bbox=[0, 0, 1, 1]),
            OcrLine(text="主队C vs 客队D 负 2.00", confidence=0.9, bbox=[0, 0, 1, 1]),
        ]
```

- [ ] **Step 4: Implement minimal TicketParser (regex only)**

```python
import re

from app.domain.ocr.ocr_service import OcrLine
from app.domain.tickets.models import Ticket, TicketDraft


def parse_ticket(lines: list[OcrLine], source_images: list[str]) -> TicketDraft:
    text = "\n".join(l.text for l in lines)
    multiplier = int(re.search(r"倍投\\s*(\\d+)", text).group(1)) if "倍投" in text else 1
    pass_types = ["2x1"] if "2串1" in text else ["1x1"]

    legs = []
    for l in lines:
        m = re.search(r"(.+?)\\s+(胜|平|负)\\s+(\\d+\\.\\d+)", l.text)
        if m:
            match_key = m.group(1).strip()
            legs.append({"matchKey": match_key, "selection": m.group(2), "sp": float(m.group(3))})

    ticket = Ticket(playType="SPF", multiplier=multiplier, passTypes=pass_types, legs=legs)
    warnings = []
    if not legs:
        warnings.append("NO_LEGS_PARSED")

    return TicketDraft(ticket=ticket, confidence={"overall": 0.5}, warnings=warnings, sourceImages=source_images)
```

- [ ] **Step 5: Wire `/api/tickets/recognize` route to return stub result**

Expected behavior:
- Accept multipart `images[]`
- Use `StubOcrService` + `parse_ticket`
- Return `TicketDraft` JSON

- [ ] **Step 6: Run tests**

Run: `cd apps/api && uv run pytest -q`  
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add 足球计算器/apps/api/app/domain/ocr 足球计算器/apps/api/app/domain/parser 足球计算器/apps/api/app/domain/tickets/models.py 足球计算器/apps/api/app/routes
git commit -m "feat: add OCR abstraction and stub ticket parsing"
```

---

### Task 6: Tickets API (recognize/validate/calculate) + anon persistence

**Files:**
- Create: `足球计算器/apps/api/app/storage/db.py`
- Create: `足球计算器/apps/api/app/storage/anonymous_store.py`
- Create: `足球计算器/apps/api/app/routes/tickets.py`
- Modify: `足球计算器/apps/api/app/main.py`
- Test: `足球计算器/apps/api/tests/test_calculate_api.py`

- [ ] **Step 1: Write failing test for calculate API**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_calculate_api_happy_path():
    client = TestClient(app)
    ticket = {
        "ticketType": "jc-football",
        "playType": "SPF",
        "multiplier": 2,
        "passTypes": ["2x1"],
        "legs": [
            {"matchKey": "m1", "selection": "胜", "sp": 1.5},
            {"matchKey": "m2", "selection": "负", "sp": 2.0}
        ]
    }
    resp = client.post("/api/tickets/calculate", json=ticket)
    assert resp.status_code == 200
    assert "totalPayout" in resp.json()
```

- [ ] **Step 2: Implement SQLite store for anonymous records**

Schema (SQLite):
- table `tickets`:
  - `id` TEXT PRIMARY KEY
  - `anon_token` TEXT
  - `ticket_json` TEXT
  - `report_json` TEXT
  - `created_at` INTEGER

- [ ] **Step 3: Implement endpoints**
- `POST /api/tickets/recognize` → returns `TicketDraft` and creates record (returns `id`)
- `POST /api/tickets/validate` → returns `{ ok: true }` or `{ ok: false, errors: [...] }`
- `POST /api/tickets/calculate` → validates, calls results provider, calls payout engine, persists report
- `GET /api/tickets/{id}` → returns stored draft/report for frontend

- [ ] **Step 4: Run tests**

Run: `cd apps/api && uv run pytest -q`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add 足球计算器/apps/api/app/routes/tickets.py 足球计算器/apps/api/app/storage 足球计算器/apps/api/tests/test_calculate_api.py
git commit -m "feat: tickets API with validate/calculate and anonymous persistence"
```

---

### Task 7: ResultsProvider (MVP mock) + matches list endpoint

**Files:**
- Create: `足球计算器/apps/api/app/domain/results/provider.py`
- Create: `足球计算器/apps/api/app/domain/results/mock_provider.py`
- Create: `足球计算器/apps/api/app/routes/matches.py`
- Modify: `足球计算器/apps/api/app/main.py`
- Test: `足球计算器/apps/api/tests/test_matches_api.py`

- [ ] **Step 1: Implement ResultsProvider interface**

```python
class ResultsProvider:
    def get_results_by_match_keys(self, match_keys: list[str]) -> dict:
        raise NotImplementedError()
```

- [ ] **Step 2: Implement Mock provider**
- Return deterministic outcomes for known `matchKey` strings (for tests)

- [ ] **Step 3: Add `GET /api/matches?date=YYYY-MM-DD`**
- Return a small list of matches with score/outcome fields for the web list page

- [ ] **Step 4: Test + commit**

```bash
cd apps/api && uv run pytest -q
git add 足球计算器/apps/api/app/domain/results 足球计算器/apps/api/app/routes/matches.py 足球计算器/apps/api/tests/test_matches_api.py
git commit -m "feat: add MVP results provider and matches endpoint"
```

---

### Task 8: Frontend upload + recognize + correction UI (minimal but usable)

**Files:**
- Create: `足球计算器/apps/web/src/app/upload/page.tsx`
- Create: `足球计算器/apps/web/src/app/tickets/[id]/edit/page.tsx`
- Create: `足球计算器/apps/web/src/components/ImageUpload.tsx`
- Create: `足球计算器/apps/web/src/components/TicketEditor.tsx`
- Modify: `足球计算器/apps/web/src/lib/api.ts`

- [ ] **Step 1: Build `ImageUpload` component (multiple images)**

```tsx
type Props = { onFiles: (files: File[]) => void };

export function ImageUpload({ onFiles }: Props) {
  return (
    <input
      type="file"
      accept="image/*"
      multiple
      onChange={(e) => onFiles(Array.from(e.target.files ?? []))}
    />
  );
}
```

- [ ] **Step 2: Implement API client (recognize)**

```ts
export async function recognizeTicket(files: File[]) {
  const form = new FormData();
  for (const f of files) form.append("images", f);
  const resp = await fetch("http://localhost:8000/api/tickets/recognize", { method: "POST", body: form });
  if (!resp.ok) throw new Error("recognize failed");
  return resp.json();
}
```

- [ ] **Step 3: Upload page calls recognize and routes to edit page**
- On success: store `anonToken` in `localStorage` if not present, keep `ticketId`

- [ ] **Step 4: TicketEditor renders legs as editable rows**
- Editable fields: `matchKey`, `selection`, `sp`, `handicap` (only when RQSPF)
- “Add leg” / “Remove leg”

- [ ] **Step 5: Add “Validate” + “Calculate” buttons**
- Validate calls `/api/tickets/validate`
- Calculate calls `/api/tickets/calculate` then routes to report page

- [ ] **Step 6: Manual smoke test**
- Run API + Web
- Upload any image (stub OCR still returns a ticket draft) and verify you can edit and calculate

- [ ] **Step 7: Commit**

```bash
git add 足球计算器/apps/web/src
git commit -m "feat: web upload and ticket correction flow"
```

---

### Task 9: Report page + matches list page (MVP)

**Files:**
- Create: `足球计算器/apps/web/src/app/tickets/[id]/report/page.tsx`
- Create: `足球计算器/apps/web/src/app/matches/page.tsx`

- [ ] **Step 1: Report page**
- Fetch `/api/tickets/{id}` to show total payout, status, leg hits, unmatched legs

- [ ] **Step 2: Matches page**
- Fetch `/api/matches?date=today` and render list

- [ ] **Step 3: Smoke test**
- Navigate across Home → Upload → Edit → Report → Matches

- [ ] **Step 4: Commit**

```bash
git add 足球计算器/apps/web/src/app/tickets 足球计算器/apps/web/src/app/matches
git commit -m "feat: report view and matches list page"
```

---

## Plan self-review (checklist)

- Spec coverage:
  - Upload multi images ✅ Task 8
  - OCR + parse draft ✅ Task 5
  - Editable correction ✅ Task 8
  - Validate gate ✅ Task 3 + Task 6
  - Results integration (minimal) ✅ Task 7
  - Payout SPF/RQSPF + pass types + multiplier ✅ Task 4
  - Anonymous persistence ✅ Task 6
  - Schedule/results page ✅ Task 7 + Task 9
- Placeholder scan:
  - No “TBD/TODO” in steps; MVP uses mock results provider and stub OCR first, then can swap PaddleOCR later.
- Type consistency:
  - `Ticket`/`Leg` fields are stable across tasks; endpoints use consistent payloads.

