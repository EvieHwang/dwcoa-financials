# Tasks: Unit Statement Tracking

**Feature**: Unit Statement Tracking ("My Account" Section)
**Branch**: `feature/002-unit-statement-tracking`
**Generated**: 2026-01-21

---

## Task Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: Database Schema & Seed Data | 3 | Pending |
| Phase 2: Backend Core | 6 | Pending |
| Phase 3: Carryover Logic | 3 | Pending |
| Phase 4: Frontend UI | 6 | Pending |
| Phase 5: Integration & Polish | 4 | Pending |
| **Total** | **22** | |

---

## Phase 1: Database Schema & Seed Data

**Objective**: Add `auto_calculated` column and seed 2025 past due balances

- [ ] T001 [US6] Update `backend/sql/schema.sql` to add `auto_calculated INTEGER NOT NULL DEFAULT 0` column to `unit_past_dues` table definition
- [ ] T002 [US6] Create database migration in `backend/app/services/database.py` to ALTER TABLE and add column if not exists
- [ ] T003 [US2] Seed 2025 past due balances into `unit_past_dues` table (manual entries, `auto_calculated=0`):
  - Unit 101: $3,981.85
  - Unit 201: $529.00
  - Unit 203: $371.40
  - Unit 303: $625.44
  - All other units: $0.00

**Dependencies**: None (foundational)

**Note**: The 2025 past due balances are historical data not visible in bank statements. These must be hard-coded as the starting point for automatic carryover calculations going forward.

---

## Phase 2: Backend Core - Statement API

**Objective**: Create API endpoints to return statement data

### Database Layer

- [ ] T004 [US1] Add `get_total_operating_budget_annual(year)` function to `backend/app/services/database.py` - returns full annual operating budget (not YTD)
- [ ] T005 [P] [US3] Add `get_unit_payments_total(unit_number, year)` function to `database.py` - sum of dues payments for unit in year
- [ ] T006 [P] [US5] Add `get_unit_recent_payments(unit_number, year, limit=10)` function to `database.py` - list of recent payment transactions

### Route Handler

- [ ] T007 [US1] Create new file `backend/app/routes/statement.py` with `handle_get_statement(unit, year)` function implementing the statement response structure
- [ ] T008 [US5] Add `handle_get_payment_history(unit, year)` function to `statement.py` for full payment history endpoint

### Router Integration

- [ ] T009 [US1] Add statement routes to `backend/app/main.py`:
  - `GET /api/statement/{unit}` → `statement.handle_get_statement`
  - `GET /api/statement/{unit}/payments` → `statement.handle_get_payment_history`

**Dependencies**: T001-T003 must complete before T007

---

## Phase 3: Carryover Calculation Logic

**Objective**: Auto-calculate carryovers when budget is locked

- [ ] T010 [US6] Add `calculate_all_carryovers(year)` function to `database.py` - loops all units, calculates carryover using formula: (prior_budget × ownership%) + prior_past_due - prior_paid
- [ ] T011 [US6] Add `upsert_unit_past_due(unit_number, year, past_due_balance, auto_calculated)` function to `database.py` - inserts or updates with auto_calculated flag, respecting manual entries
- [ ] T012 [US6] Modify `handle_lock()` in `backend/app/routes/budgets.py` to call `calculate_all_carryovers(year)` when `locked=True`, and return carryover count in response

**Dependencies**: T004, T005 must complete before T010

---

## Phase 4: Frontend UI

**Objective**: Add unit selector and My Account section to dashboard

### Unit Selector

- [ ] T013 [US1] Add unit selector dropdown HTML to `frontend/index.html` in the header/controls area, with all 9 unit options
- [ ] T014 [US1] Add unit selector JavaScript to `frontend/app.js`:
  - Populate dropdown
  - Save selection to `localStorage.setItem('selectedUnit', ...)`
  - Restore selection on page load
  - Trigger statement load on change

### My Account Section Structure

- [ ] T015 [US1] Add "My Account" section HTML to `frontend/index.html` below Income & Dues section with:
  - Section container with id `my-account-section`
  - Prior year summary card placeholder
  - Current year summary card placeholder
  - Payment guidance card placeholder
  - Recent payments table placeholder

### Statement Rendering

- [ ] T016 [US2][US3] Add `renderMyAccount(data)` function to `app.js` to populate:
  - Prior year: annual dues budgeted, total paid, balance carried forward
  - Current year: carryover, annual dues, total due, paid YTD, remaining balance
  - Payment guidance: standard monthly, suggested monthly, months remaining
  - Recent payments table

- [ ] T017 [US1] Add `loadStatement(unit)` function to `app.js` to fetch from `/api/statement/{unit}` and call `renderMyAccount()`

### Styling

- [ ] T018 [P] [US1] Add My Account section CSS to `frontend/styles.css`:
  - Card layout matching existing dashboard style
  - Highlight colors for key numbers (remaining balance, suggested monthly)
  - Color coding: green for paid/credit, amber for on-track, red for behind
  - Responsive styles for mobile

**Dependencies**: T009 must complete before T017 can be tested

---

## Phase 5: Integration & Polish

**Objective**: Handle edge cases and finalize the feature

- [ ] T019 [US2] Add handling for "no prior year data" state - display "No data available for [year]" message in prior year section
- [ ] T020 [US3] Add handling for unlocked budget state - display "Budget for [year] is pending approval. Amounts shown are preliminary." notice
- [ ] T021 [US4] Add edge case handling in payment guidance:
  - If `remaining_balance <= 0`: show "Paid in full" or "Credit balance: $X"
  - If December: show "Remaining balance: $X due by Dec 31"
  - Credit display format: "($150.00) credit"
- [ ] T022 [US5] Add "View full payment history" link/button that calls `/api/statement/{unit}/payments` and displays in modal or expanded section

**Dependencies**: T016 must complete before T019-T022

---

## Dependency Graph

```
T001 ─► T002 ─► T003 ─┬─► T007 ─► T009 ─► T017
                      │
T004 ─┬─► T005 ───────┼─► T010 ─► T011 ─► T012
      │               │
      └─► T006 ───────┘

T013 ─► T014 ─► T015 ─► T016 ─► T018
                          │
                          └─► T019 ─► T020 ─► T021 ─► T022
```

**Parallel Work Streams**:
- Stream A: Database + Backend API (T001-T012)
- Stream B: Frontend UI (T013-T018) - can start T013-T015 in parallel with backend

---

## User Story Coverage

| User Story | Tasks | Priority |
|------------|-------|----------|
| US1: Select Unit and View Statement | T001-T009, T013-T018 | P1 |
| US2: View Last Year Summary | T003, T007, T016, T019 | P2 |
| US3: View Current Year Summary | T005, T007, T016, T020 | P1 |
| US4: View Payment Guidance | T007, T016, T021 | P2 |
| US5: View Recent Payments | T006, T008, T016, T022 | P3 |
| US6: Automatic Carryover on Budget Lock | T001, T002, T010-T012 | P2 |

---

## Verification Checklist

After all tasks complete:

- [ ] Unit selector dropdown shows all 9 units
- [ ] Selected unit persists across page refresh (localStorage)
- [ ] Statement loads within 3 seconds
- [ ] Prior year shows: budgeted, paid, carryover
- [ ] Current year shows: total due, paid YTD, remaining
- [ ] Payment guidance shows suggested monthly
- [ ] Recent payments table displays
- [ ] Budget lock triggers carryover calculation
- [ ] Manual past due entries are NOT overwritten
- [ ] Credit balances display correctly
- [ ] "No data" states display appropriate messages
- [ ] Responsive on mobile viewport
