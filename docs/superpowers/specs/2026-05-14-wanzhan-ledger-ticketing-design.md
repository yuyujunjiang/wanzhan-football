# Wanzhan Ledger Ticketing Design

## Goal

Rebuild the Wanzhan ledger flow around database-backed tickets:

- Let users select betting options directly from schedule and results pages.
- Create pending tickets from upcoming matches.
- Create immediately settled ledger entries from finished matches.
- Automatically settle pending tickets once all selected matches have results.
- Show pending and settled ticket information in the ledger, with daily profit derived from settled tickets.

## Confirmed Decisions

- Pass type is fixed `Nx1`.
- `Nx1` means all selected matches must hit to win.
- For fixed `Nx1`, stake is `2 * multiplier` regardless of `N`.
- Estimated payout is `2 * multiplier * product(selected odds)`.
- Settlement payout is either estimated payout when all legs hit, or `0` when any leg misses.
- Ledger storage uses SQLite as the single source of truth.
- The current grey/white visual style is approved.
- Schedule and results pages both allow selection.
- Results-page tickets settle immediately because results are already known.

## Data Model

Use SQLite for both pending and settled tickets. Replace the current frontend-only `localStorage` ledger as the authoritative source.

### `ledger_tickets`

Represents one user ticket.

- `id`: primary key
- `date`: ticket date, local `YYYY-MM-DD`
- `status`: `pending` or `settled`
- `pass_type`: fixed `Nx1`
- `multiplier`: integer multiplier
- `stake`: `2 * multiplier`
- `estimated_payout`: maximum possible payout
- `actual_payout`: settled payout, `0` while pending
- `profit`: `actual_payout - stake`, counted only after settlement
- `created_at`
- `settled_at`

### `ledger_legs`

Represents each selected match inside a ticket.

- `ticket_id`
- `match_key`
- `match_id`
- `league`
- `home_team`
- `away_team`
- `kickoff_time`
- `play_type`: `SPF` or `RQSPF`
- `selection`: `胜`, `平`, `负`, `让胜`, `让平`, or `让负`
- `sp`
- `handicap`
- `result_selection`
- `is_hit`

This schema supports mixed tickets because each leg owns its own play type.

## Schedule And Results Selection

Both the schedule and results views render clickable odds buttons.

Each match shows six possible options:

- `SPF`: `胜`, `平`, `负`
- `RQSPF`: `让胜`, `让平`, `让负`

Selection rules:

- A match may have at most one selected option.
- Selecting an SPF option clears any RQSPF option for the same match.
- Selecting an RQSPF option clears any SPF option for the same match.
- Clicking the selected option again clears it.
- Unselected buttons use white background, grey border, dark text.
- Selected buttons use dark grey or black background with white text.

When at least one match is selected, show a floating bottom-right button:

- Schedule mode: `出票 · N场`
- Results mode: `补记 · N场`

## Ticket Confirmation

Clicking the floating button opens a confirmation sheet.

The sheet shows:

- Selected matches and selections
- Fixed pass type `Nx1`
- Multiplier input, default `1`
- Stake
- Estimated payout

Calculations:

- `stake = 2 * multiplier`
- `estimated_payout = round2(2 * multiplier * product(sp values))`
- `pass_type = "{selected_count}x1"`

Schedule mode submit:

- Creates a `pending` ticket.
- Clears current selections.
- Updates pending ticket count.

Results mode submit:

- Creates a ticket and immediately attempts settlement.
- If all selected legs hit, creates a settled winning ticket.
- If any selected leg misses, creates a settled losing ticket.
- Updates ledger summary immediately.

## Settlement

Settlement runs in two ways:

- Background scheduler scans pending tickets periodically.
- Page/API access triggers a lightweight settlement pass as a fallback.

Settlement logic:

1. Load pending tickets.
2. For each ticket, find results for all legs.
3. If any leg has no result, keep the ticket pending.
4. If all legs have results, compare each leg:
   - `SPF` uses `outcomeSPF`.
   - `RQSPF` uses `outcomeRQSPF`.
5. Fixed `Nx1` wins only if every leg is hit.
6. On win:
   - `actual_payout = estimated_payout`
   - `profit = estimated_payout - stake`
7. On loss:
   - `actual_payout = 0`
   - `profit = -stake`
8. Update ticket to `settled`.
9. Write each leg's `result_selection` and `is_hit`.

Settlement is idempotent. Running it multiple times must not duplicate ledger entries or change settled tickets unexpectedly.

## API Surface

Add a new ledger router under `/api/ledger`.

### `POST /api/ledger/tickets`

Creates a schedule or results ticket.

Input includes:

- `mode`: `schedule` or `results`
- `date`
- `multiplier`
- selected legs copied from match cards

Output returns the created ticket, status, stake, estimated payout, actual payout, and profit.

### `POST /api/ledger/settle`

Runs settlement for pending tickets.

Used by page-access fallback and manual refresh.

### `GET /api/ledger/summary?start=&end=`

Returns:

- `stake`
- `payout`
- `profit`
- `pendingCount`
- `settledCount`
- `ticketCount`

Profit and payout are based on settled tickets. Pending tickets contribute to stake and pending count, but not payout or profit.

### `GET /api/ledger/tickets?date=&start=&end=&status=`

Returns ticket list for ledger pages.

Supports:

- `status=all`
- `status=pending`
- `status=settled`

### `GET /api/ledger/tickets/{id}`

Returns full ticket detail with legs.

## Ledger UI

The ledger keeps the current day/week/month structure but reads from the backend.

Top summary shows:

- 投入
- 回报
- 盈亏
- 待结票数量
- 已结票数量

The Wanzhan `StatStrip` shows:

- Today's settled profit
- All pending ticket count

Pending ticket cards show:

- `Nx1`
- multiplier
- stake
- estimated payout
- selected match summary
- pending status

Settled ticket cards show:

- winning or losing status
- stake
- actual payout
- profit
- selected match summary

Ticket details show each leg:

- match
- play type
- selection
- SP
- result
- hit or miss

## Error Handling

- If odds are missing for a selected option, disable that option.
- If a user tries to submit with no selections, block submit.
- If results are missing for schedule tickets, keep them pending.
- If results-page submission contains a match without known outcome, create pending instead of settled.
- If settlement fails due to provider/network issues, keep existing ticket state and retry later.

## Testing

Backend tests:

- Creating fixed `Nx1` tickets computes stake and estimated payout correctly.
- A schedule ticket is created as pending when results are unavailable.
- A results ticket settles immediately when all results are present.
- Fixed `Nx1` wins only when all legs hit.
- Losing tickets settle with payout `0` and profit `-stake`.
- Settlement is idempotent.
- Summary aggregates date ranges correctly.

Frontend tests or focused manual verification:

- One match cannot hold both SPF and RQSPF selections.
- Re-clicking a selected option clears it.
- Floating button appears only when selections exist.
- Confirmation sheet computes stake and estimated payout as multiplier changes.
- Ledger pages show pending and settled tickets from backend data.

## Implementation Notes

- Keep the existing match provider and cached Sporttery data as the result source.
- Move ledger behavior out of `apps/web/src/lib/wanzhanLedger.ts` and into API calls.
- Keep old OCR/upload ticket flow separate from this schedule-based ticketing flow.
- Use the approved grey/white design for selectable odds and ledger cards.
