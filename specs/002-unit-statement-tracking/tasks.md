# Tasks: Unit Statement Tracking

**Feature**: Unit Statement Tracking ("My Account" Section)
**Branch**: `feature/002-unit-statement-tracking`
**Generated**: 2026-01-21

---

## Task Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: Database Schema | 2 | Pending |
| Phase 2: Backend Core | 6 | Pending |
| Phase 3: Carryover Logic | 3 | Pending |
| Phase 4: Frontend UI | 6 | Pending |
| Phase 5: Integration & Polish | 4 | Pending |
| **Total** | **21** | |

---

## Phase 1: Database Schema

**Objective**: Add `auto_calculated` column to track carryover source

- [ ] T001 [US6] Update `backend/sql/schema.sql` to add `auto_calculated INTEGER NOT NULL DEFAULT 0` column to `unit_past_dues` table definition
- [ ] T002 [US6] Create database migration in `backend/app/services/database.py` to ALTER TABLE and add column if not exists

**Dependencies**: None (foundational)

---

## Phase 2: Backend Core - Statement API

**Objective**: Create API endpoints to return statement data

### Database Layer

- [ ] T003 [US1] Add `get_total_operating_budget_annual(year)` function to `backend/app/services/database.py` - returns full annual operating budget (not YTD)
- [ ] T004 [P] [US3] Add `get_unit_payments_total(unit_number, year)` function to `database.py` - sum of dues payments for unit in year
- [ ] T005 [P] [US5] Add `get_unit_recent_payments(unit_number, year, limit=10)` function to `database.py` - list of recent payment transactions

### Route Handler

- [ ] T006 [US1] Create new file `backend/app/routes/statement.py` with `handle_get_statement(unit, year)` function implementing the statement response structure
- [ ] T007 [US5] Add `handle_get_payment_history(unit, year)` function to `statement.py` for full payment history endpoint

### Router Integration

- [ ] T008 [US1] Add statement routes to `backend/app/main.py`:
  - `GET /api/statement/{unit}` → `statement.handle_get_statement`
  - `GET /api/statement/{unit}/payments` → `statement.handle_get_payment_history`

**Dependencies**: T001, T002 must complete before T006

---

## Phase 3: Carryover Calculation Logic

**Objective**: Auto-calculate carryovers when budget is locked

- [ ] T009 [US6] Add `calculate_all_carryovers(year)` function to `database.py` - loops all units, calculates carryover using formula: (prior_budget × ownership%) + prior_past_due - prior_paid
- [ ] T010 [US6] Add `upsert_unit_past_due(unit_number, year, past_due_balance, auto_calculated)` function to `database.py` - inserts or updates with auto_calculated flag, respecting manual entries
- [ ] T011 [US6] Modify `handle_lock()` in `backend/app/routes/budgets.py` to call `calculate_all_carryovers(year)` when `locked=True`, and return carryover count in response

**Dependencies**: T003, T004 must complete before T009

---

## Phase 4: Frontend UI

**Objective**: Add unit selector and My Account section to dashboard

### Unit Selector

- [ ] T012 [US1] Add unit selector dropdown HTML to `frontend/index.html` in the header/controls area, with all 9 unit options
- [ ] T013 [US1] Add unit selector JavaScript to `frontend/app.js`:
  - Populate dropdown
  - Save selection to `localStorage.setItem('selectedUnit', ...)`
  - Restore selection on page load
  - Trigger statement load on change

### My Account Section Structure

- [ ] T014 [US1] Add "My Account" section HTML to `frontend/index.html` below Income & Dues section with:
  - Section container with id `my-account-section`
  - Prior year summary card placeholder
  - Current year summary card placeholder
  - Payment guidance card placeholder
  - Recent payments table placeholder

### Statement Rendering

- [ ] T015 [US2][US3] Add `renderMyAccount(data)` function to `app.js` to populate:
  - Prior year: annual dues budgeted, total paid, balance carried forward
  - Current year: carryover, annual dues, total due, paid YTD, remaining balance
  - Payment guidance: standard monthly, suggested monthly, months remaining
  - Recent payments table

- [ ] T016 [US1] Add `loadStatement(unit)` function to `app.js` to fetch from `/api/statement/{unit}` and call `renderMyAccount()`

### Styling

- [ ] T017 [P] [US1] Add My Account section CSS to `frontend/styles.css`:
  - Card layout matching existing dashboard style
  - Highlight colors for key numbers (remaining balance, suggested monthly)
  - Color coding: green for paid/credit, amber for on-track, red for behind
  - Responsive styles for mobile

**Dependencies**: T008 must complete before T016 can be tested

---

## Phase 5: Integration & Polish

**Objective**: Handle edge cases and finalize the feature

- [ ] T018 [US2] Add handling for "no prior year data" state - display "No data available for [year]" message in prior year section
- [ ] T019 [US3] Add handling for unlocked budget state - display "Budget for [year] is pending approval. Amounts shown are preliminary." notice
- [ ] T020 [US4] Add edge case handling in payment guidance:
  - If `remaining_balance <= 0`: show "Paid in full" or "Credit balance: $X"
  - If December: show "Remaining balance: $X due by Dec 31"
  - Credit display format: "($150.00) credit"
- [ ] T021 [US5] Add "View full payment history" link/button that calls `/api/statement/{unit}/payments` and displays in modal or expanded section

**Dependencies**: T015 must complete before T018-T021

---

## Dependency Graph

```
T001 ─┬─► T002 ─┬─► T006 ─► T008 ─► T016
      │        │
T003 ─┤        └─► T009 ─► T010 ─► T011
      │
T004 ─┼─► T005
      │
      └─► T012 ─► T013 ─► T014 ─► T015 ─► T017
                                    │
                                    └─► T018 ─► T019 ─► T020 ─► T021
```

**Parallel Work Streams**:
- Stream A: Database + Backend API (T001-T011)
- Stream B: Frontend UI (T012-T017) - can start T012-T014 in parallel with backend

---

## User Story Coverage

| User Story | Tasks | Priority |
|------------|-------|----------|
| US1: Select Unit and View Statement | T001-T008, T012-T017 | P1 |
| US2: View Last Year Summary | T006, T015, T018 | P2 |
| US3: View Current Year Summary | T004, T006, T015, T019 | P1 |
| US4: View Payment Guidance | T006, T015, T020 | P2 |
| US5: View Recent Payments | T005, T007, T015, T021 | P3 |
| US6: Automatic Carryover on Budget Lock | T001, T002, T009-T011 | P2 |

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
