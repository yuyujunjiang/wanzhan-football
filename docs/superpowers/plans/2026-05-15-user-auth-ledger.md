# User Auth + Ledger Isolation + Ticket CRUD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require login for all `/wanzhan/*` routes; persist users in SQLite; scope ledger tickets per user; add PATCH/DELETE for ledger tickets (pending = structural edit, settled = stake/payout only per option B).

**Architecture:** FastAPI session table + HttpOnly `fc_session` cookie (30 days). `get_current_user` dependency guards `/api/ledger/*`. `LedgerStore` filters by `user_id`. Next.js middleware redirects unauthenticated users to `/wanzhan/login`; `apiFetch` uses `credentials: "include"`. CLI provisions users with bcrypt hashes.

**Tech Stack:** FastAPI, Pydantic v2, SQLite, `bcrypt`, pytest + TestClient, Next.js App Router (TypeScript).

**Spec:** `docs/superpowers/specs/2026-05-15-user-auth-ledger-design.md`

**Worktree:** `/Users/yujj/Documents/New project/.worktrees/football-calculator-mvp`

---

## File map

| File | Responsibility |
|------|----------------|
| `apps/api/app/domain/auth/models.py` | `UserOut`, `LoginRequest`, session DTOs |
| `apps/api/app/domain/auth/passwords.py` | `hash_password`, `verify_password` |
| `apps/api/app/storage/user_store.py` | `users` CRUD |
| `apps/api/app/storage/session_store.py` | create/get/delete sessions |
| `apps/api/app/auth/deps.py` | `get_current_user`, cookie name constant |
| `apps/api/app/routes/auth.py` | login / logout / me |
| `apps/api/app/tools/create_user.py` | CLI entry |
| `apps/api/app/storage/db.py` | migrate `users`, `sessions`, `ledger_tickets.user_id` |
| `apps/api/app/storage/ledger_store.py` | all queries scoped; update/delete |
| `apps/api/app/routes/ledger.py` | auth + PATCH + DELETE |
| `apps/api/app/main.py` | include auth router |
| `apps/api/tests/test_auth_api.py` | auth tests |
| `apps/api/tests/test_ledger_api.py` | add auth helpers; 401 without login |
| `apps/api/tests/test_ledger_crud_api.py` | patch/delete tests |
| `apps/web/src/middleware.ts` | protect `/wanzhan/*` |
| `apps/web/src/app/wanzhan/login/page.tsx` | login form |
| `apps/web/src/lib/api.ts` | credentials + auth + ledger CRUD |
| `apps/web/src/app/wanzhan/ledger/tickets/[id]/edit/page.tsx` | edit UI |
| `apps/web/src/app/wanzhan/ledger/day/[date]/page.tsx` | list edit/delete buttons |
| `apps/web/src/app/wanzhan/ledger/tickets/[id]/page.tsx` | detail edit/delete |
| `apps/web/src/app/wanzhan/me/page.tsx` | username + logout |

---

## Local commands

```bash
# API (from worktree root)
cd apps/api && uv sync && uv run pytest -q
cd apps/api && uv run uvicorn app.main:app --reload --port 8000

# Web
cd apps/web && npm run dev

# Create first user
cd apps/api && uv run python -m app.tools.create_user --username admin --password 'your-secret'
```

---

### Task 1: Add bcrypt dependency

**Files:**
- Modify: `apps/api/pyproject.toml`

- [ ] **Step 1: Add dependency**

In `[project].dependencies` add:

```toml
  "bcrypt>=4.1",
```

- [ ] **Step 2: Lock deps**

Run: `cd apps/api && uv sync`  
Expected: exit 0

- [ ] **Step 3: Commit**

```bash
git add apps/api/pyproject.toml apps/api/uv.lock
git commit -m "chore(api): add bcrypt for password hashing"
```

---

### Task 2: Password helpers

**Files:**
- Create: `apps/api/app/domain/auth/__init__.py` (empty)
- Create: `apps/api/app/domain/auth/passwords.py`
- Create: `apps/api/tests/test_auth_passwords.py`

- [ ] **Step 1: Write failing test**

```python
# apps/api/tests/test_auth_passwords.py
from app.domain.auth.passwords import hash_password, verify_password


def test_hash_and_verify_password():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)
```

- [ ] **Step 2: Run test (fail)**

Run: `cd apps/api && uv run pytest tests/test_auth_passwords.py -v`  
Expected: FAIL (module missing)

- [ ] **Step 3: Implement**

```python
# apps/api/app/domain/auth/passwords.py
from __future__ import annotations

import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
```

- [ ] **Step 4: Run test (pass)**

Run: `cd apps/api && uv run pytest tests/test_auth_passwords.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/domain/auth apps/api/tests/test_auth_passwords.py
git commit -m "feat(api): add bcrypt password helpers"
```

---

### Task 3: DB migration — users, sessions, ledger user_id

**Files:**
- Modify: `apps/api/app/storage/db.py`
- Create: `apps/api/tests/test_auth_db_migration.py`

- [ ] **Step 1: Write failing test**

```python
# apps/api/tests/test_auth_db_migration.py
import sqlite3
from pathlib import Path

from app.storage.db import connect, migrate


def test_migrate_creates_users_sessions_and_ledger_user_id(tmp_path):
    path = tmp_path / "t.sqlite3"
    conn = sqlite3.connect(path)
    migrate(conn)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "users" in tables
    assert "sessions" in tables
    cols = [row[1] for row in conn.execute("PRAGMA table_info(ledger_tickets)")]
    assert "user_id" in cols
    conn.close()
```

- [ ] **Step 2: Run test (fail)**

Run: `cd apps/api && uv run pytest tests/test_auth_db_migration.py -v`

- [ ] **Step 3: Extend `migrate()`**

Add after existing `ledger_tickets` CREATE (or alter flow):

```python
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")

    # ledger_tickets.user_id — fresh DB gets NOT NULL; existing DB migration:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(ledger_tickets)")}
    if "user_id" not in cols:
        conn.execute("DELETE FROM ledger_legs")
        conn.execute("DELETE FROM ledger_tickets")
        conn.execute("ALTER TABLE ledger_tickets ADD COLUMN user_id TEXT NOT NULL DEFAULT ''")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ledger_tickets_user_date ON ledger_tickets(user_id, date)")
```

Remove `DEFAULT ''` in a follow-up migration step if you recreate table instead — for tests always fresh DB. Document in code comment: production upgrade clears ledger per spec.

- [ ] **Step 4: Run test (pass)**

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/storage/db.py apps/api/tests/test_auth_db_migration.py
git commit -m "feat(api): migrate users, sessions, ledger user_id"
```

---

### Task 4: UserStore + SessionStore

**Files:**
- Create: `apps/api/app/storage/user_store.py`
- Create: `apps/api/app/storage/session_store.py`
- Create: `apps/api/app/domain/auth/models.py`
- Create: `apps/api/tests/test_user_session_store.py`

- [ ] **Step 1: Models**

```python
# apps/api/app/domain/auth/models.py
from pydantic import BaseModel, Field


class UserOut(BaseModel):
    id: str
    username: str


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
```

- [ ] **Step 2: Failing store test** — create user, create session, get by id, delete session.

- [ ] **Step 3: Implement stores** with `normalize_username(s: str) -> str` as `s.strip().lower()`.

- [ ] **Step 4: pytest pass**

- [ ] **Step 5: Commit**

---

### Task 5: Auth routes + get_current_user

**Files:**
- Create: `apps/api/app/auth/deps.py`
- Create: `apps/api/app/routes/auth.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/test_auth_api.py`

Constants in `deps.py`:

```python
SESSION_COOKIE = "fc_session"
SESSION_MAX_AGE = 30 * 24 * 60 * 60
```

`login`: verify user → `session_store.create(user_id, expires_at=now+SESSION_MAX_AGE)` → `JSONResponse` with `set_cookie(SESSION_COOKIE, session_id, httponly=True, max_age=SESSION_MAX_AGE, samesite="lax", path="/")`.

`get_current_user`: read cookie → load session → if expired delete → 401 else `UserOut`.

- [ ] **Tests:** login 200 + me 200; bad password 401; logout clears me.

- [ ] **Register router** in `main.py`: `app.include_router(auth_router)`

- [ ] **Commit**

---

### Task 6: CLI create_user

**Files:**
- Create: `apps/api/app/tools/__init__.py`
- Create: `apps/api/app/tools/create_user.py`
- Create: `apps/api/tests/test_create_user_cli.py`

```python
# apps/api/app/tools/create_user.py — argparse --username --password
# exit 1 if username exists; print created id to stdout (not password)
```

Test via `subprocess` or call `main()` with monkeypatched env `FC_SQLITE_PATH`.

- [ ] **Commit**

---

### Task 7: LedgerStore user_id scoping

**Files:**
- Modify: `apps/api/app/storage/ledger_store.py`
- Modify: `apps/api/tests/test_ledger_store.py`
- Modify: `apps/api/tests/test_ledger_api.py`

- [ ] **Step 1: Change signatures** — `create_ticket(..., user_id: str)`, `get_ticket(ticket_id, user_id)`, `list_tickets(..., user_id)`, `summary(..., user_id)`, `settle_ticket(..., user_id)`, etc.

- [ ] **Step 2: SQL** — every `ledger_tickets` query adds `user_id = ?`.

- [ ] **Step 3: Add methods**

```python
def delete_ticket(self, *, user_id: str, ticket_id: str) -> bool: ...
def update_ticket_pending(self, *, user_id: str, ticket_id: str, ...) -> LedgerTicketOut | None: ...
def update_ticket_settled(self, *, user_id: str, ticket_id: str, stake: float, actual_payout: float) -> LedgerTicketOut | None: ...
```

Pending update: delete legs for ticket, re-insert, recompute stake/estimated, reset settlement fields.

- [ ] **Step 4: Fix existing ledger tests** — pass a fixture `user_id` by creating user in DB or use constant in tests with direct store calls.

- [ ] **Step 5: Commit**

---

### Task 8: Ledger routes — auth, PATCH, DELETE

**Files:**
- Modify: `apps/api/app/routes/ledger.py`
- Modify: `apps/api/app/domain/ledger/models.py` — add `LedgerTicketUpdate`, `LedgerTicketSettledUpdate`
- Create: `apps/api/tests/test_ledger_crud_api.py`
- Create: `apps/api/tests/conftest.py` (optional shared `authed_client` fixture)

**Helper for tests:**

```python
def _login(client, username="alice", password="pw"):
    client.post("/api/auth/login", json={"username": username, "password": password})

def _register_user(store, username, password):
    ...
```

- [ ] **Every endpoint** adds `user: UserOut = Depends(get_current_user)`.

- [ ] **PATCH `/api/ledger/tickets/{ticket_id}`**
  - Load ticket; 404 if missing/wrong user.
  - If `status == "pending"`: body `LedgerTicketUpdate` → `update_ticket_pending`.
  - If `status == "settled"`: body `LedgerTicketSettledUpdate` only; if body contains legs → 400 `"settled tickets cannot change legs"`.
  - Optional query `reSettle=true` on pending path only.

- [ ] **DELETE** → 204

- [ ] **Tests:**
  - unauthenticated ledger → 401
  - user A cannot GET user B ticket → 404
  - delete then get → 404
  - patch pending multiplier changes stake
  - patch settled rejects legs payload
  - patch settled updates profit

- [ ] **Commit**

---

### Task 9: Frontend — api.ts auth + credentials + ledger CRUD

**Files:**
- Modify: `apps/web/src/lib/api.ts`

- [ ] **Step 1:** Add to `apiFetch`:

```typescript
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers,
    body: ...
  });
```

- [ ] **Step 2:** Add functions:

```typescript
export type AuthUser = { id: string; username: string };

export async function login(username: string, password: string): Promise<AuthUser> { ... }
export async function logout(): Promise<void> { ... }
export async function getMe(): Promise<AuthUser> { ... }

export async function updateLedgerTicket(id: string, body: ...): Promise<LedgerTicket> { ... }
export async function deleteLedgerTicket(id: string): Promise<void> { ... }
```

- [ ] **Step 3:** On 401 outside login page, `window.location.href = "/wanzhan/login?next=..."` (client components only).

- [ ] **Commit** (no separate test unless project has frontend tests; manual check noted in Task 12)

---

### Task 10: Login page + me logout

**Files:**
- Create: `apps/web/src/app/wanzhan/login/page.tsx`
- Modify: `apps/web/src/app/wanzhan/me/page.tsx`

Login: controlled inputs, submit → `login()` → `router.replace(searchParams.get("next") ?? "/wanzhan/matches")`.

Me: `useEffect` load `getMe()`; logout button → `logout()` → redirect login.

- [ ] **Commit**

---

### Task 11: Next.js middleware

**Files:**
- Create: `apps/web/src/middleware.ts`

```typescript
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC = "/wanzhan/login";

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (!pathname.startsWith("/wanzhan")) return NextResponse.next();
  if (pathname === PUBLIC || pathname.startsWith(PUBLIC + "/")) {
    return NextResponse.next();
  }

  const cookie = request.cookies.get("fc_session");
  if (!cookie?.value) {
    const url = request.nextUrl.clone();
    url.pathname = PUBLIC;
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  // Optional: server-side validate via internal fetch to /api/auth/me using forwarded cookie
  return NextResponse.next();
}

export const config = { matcher: ["/wanzhan/:path*"] };
```

Note: cookie presence check is enough for redirect; API still enforces auth.

- [ ] **Commit**

---

### Task 12: Ledger edit/delete UI

**Files:**
- Modify: `apps/web/src/app/wanzhan/ledger/day/[date]/page.tsx`
- Modify: `apps/web/src/app/wanzhan/ledger/tickets/[id]/page.tsx`
- Create: `apps/web/src/app/wanzhan/ledger/tickets/[id]/edit/page.tsx`
- Optional: `apps/web/src/components/wanzhan/LedgerTicketActions.tsx`

**Day list:** Replace single `<a>` card with a container:
- Title area links to detail
- Buttons: 编辑 → `/wanzhan/ledger/tickets/{id}/edit`, 删除 → `confirm` → `deleteLedgerTicket` → reload list

**Edit page (pending):** Load ticket; form for date, multiplier, legs (min 1); reuse field layout from upload flow if available; save → `updateLedgerTicket`.

**Edit page (settled):** Only stake + actualPayout inputs; save → PATCH settled body.

**Detail:** Edit / Delete buttons in header.

- [ ] **Manual test checklist**
  - Login → lands on matches
  - Create ticket → appears in day list
  - Edit pending multiplier → stake updates
  - Settle (or create results mode) → edit only stake/payout
  - Delete removes from list

- [ ] **Commit**

---

### Task 13: Remove dead localStorage ledger (if unused)

**Files:**
- Check: `apps/web/src/lib/wanzhanLedger.ts` references

- [ ] If zero imports, delete file.

- [ ] **Commit** (or skip with comment if still referenced)

---

### Task 14: Deployment note

**Files:**
- Modify: `DEPLOYMENT.md` (if present) — add create_user command + cookie Secure in production

- [ ] **Commit**

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| CLI users, no registration | 6 |
| Username login | 5 |
| HttpOnly cookie 30d | 5 |
| Login → /wanzhan/matches | 10 |
| /wanzhan/* protected | 11 |
| ledger user_id | 3, 7, 8 |
| PATCH/DELETE ledger | 7, 8, 12 |
| Pending structural edit | 7, 8, 12 |
| Settled B (stake/payout only) | 8, 12 |
| No OCR/matches auth | 8 (ledger only) |
| credentials include | 9 |

## Plan self-review

- No TBD placeholders in task steps.
- Settled legs rejection covered in Task 8.
- Existing `test_ledger_api.py` must gain auth — Task 7/8 explicitly.

---

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-05-15-user-auth-ledger.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — implement in this session with executing-plans checkpoints  

Which approach do you want?
