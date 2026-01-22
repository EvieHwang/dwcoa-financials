# Technical Plan: Unit Statement Tracking

**Feature**: Unit Statement Tracking ("My Account" Section)
**Branch**: `feature/002-unit-statement-tracking`
**Created**: 2026-01-21

---

## Technical Context

| Aspect | Value |
|--------|-------|
| **Language** | Python 3.12 (backend), Vanilla JavaScript (frontend) |
| **Framework** | AWS Lambda + API Gateway |
| **Database** | SQLite (stored in S3) |
| **Frontend** | Static HTML/CSS/JS hosted on S3 + CloudFront |
| **Auth** | JWT tokens, shared passwords (board/admin roles) |
| **Build Tool** | AWS SAM |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ┌──────────────┐  ┌──────────────────────────────────────┐ │
│  │ Unit Selector │  │         My Account Section           │ │
│  │   Dropdown    │  │  ┌────────────┬───────────────────┐  │ │
│  │               │  │  │Last Year   │ Current Year      │  │ │
│  │ localStorage  │  │  │Summary     │ Summary           │  │ │
│  │ persistence   │  │  ├────────────┼───────────────────┤  │ │
│  └──────────────┘  │  │Payment     │ Payment Guidance  │  │ │
│                     │  │History     │ Suggested Monthly │  │ │
│                     │  └────────────┴───────────────────┘  │ │
│                     └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway                              │
│  GET /api/statement/{unit}                                  │
│  GET /api/statement/{unit}/payments                         │
│  POST /api/budgets/lock/{year} (modified)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Lambda Function                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ routes/statement.py (NEW)                              │ │
│  │  - get_statement(unit, year)                           │ │
│  │  - get_payment_history(unit, year)                     │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ routes/budgets.py (MODIFIED)                           │ │
│  │  - handle_lock() + carryover calculation               │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ services/database.py (EXTENDED)                        │ │
│  │  - get_unit_statement_data()                           │ │
│  │  - calculate_carryovers()                              │ │
│  │  - upsert_unit_past_due() with auto_calculated flag    │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      SQLite (S3)                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ unit_past_dues (MODIFIED)                              │ │
│  │  + auto_calculated INTEGER DEFAULT 0                   │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ transactions, budgets, units, categories (unchanged)   │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Constitution Alignment

| Principle | How This Feature Complies |
|-----------|--------------------------|
| **Simplicity First** | Single new API endpoint, minimal schema change (1 column), vanilla JS frontend |
| **Serverless When Dynamic** | Uses existing Lambda, no new infrastructure |
| **Password-Protected Access** | Leverages existing JWT auth, no new auth required |
| **Data Portability** | Statement data derived from existing transactions/budgets |
| **Cost Guardrails** | No new compute resources, trivial query cost |

---

## File Changes Summary

### New Files

| File | Purpose |
|------|---------|
| `backend/app/routes/statement.py` | Statement API endpoints |

### Modified Files

| File | Changes |
|------|---------|
| `backend/sql/schema.sql` | Add `auto_calculated` column |
| `backend/app/services/database.py` | Add statement query functions, carryover logic |
| `backend/app/routes/budgets.py` | Call carryover calculation on lock |
| `backend/app/main.py` | Add statement route handlers |
| `frontend/index.html` | Add unit selector, My Account section |
| `frontend/app.js` | Add statement fetch/render logic |
| `frontend/styles.css` | Add My Account section styles |

---

## Implementation Phases

### Phase 1: Database Schema (Low Risk)

**Objective**: Add `auto_calculated` flag to track carryover source

**Changes**:
1. Update `schema.sql` with new column definition
2. Create migration script to ALTER existing table
3. Apply migration to production database

**Verification**: Query `unit_past_dues` shows new column

---

### Phase 2: Backend - Statement Endpoint (Medium Risk)

**Objective**: Create API to return statement data for a unit

**Changes**:
1. Create `routes/statement.py` with:
   - `handle_get_statement(unit, year)`
   - `handle_get_payment_history(unit, year)`
2. Add to `database.py`:
   - `get_total_operating_budget_annual(year)` - full year budget (not YTD)
   - `get_unit_payments(unit, year)` - sum of dues payments
   - `get_recent_payments(unit, year, limit)` - payment list
3. Wire routes in `main.py`

**Verification**: cURL requests return expected JSON structure

---

### Phase 3: Backend - Carryover Calculation (Medium Risk)

**Objective**: Auto-calculate carryovers when budget is locked

**Changes**:
1. Add to `database.py`:
   - `calculate_all_carryovers(year)` - loop all units, calc & store
   - `upsert_unit_past_due(unit, year, balance, auto_calculated)`
2. Modify `budgets.py` `handle_lock()`:
   - After setting lock, if `locked=True`, call carryover calculation
   - Return count of carryovers calculated

**Verification**: Lock budget, check `unit_past_dues` has entries with `auto_calculated=1`

---

### Phase 4: Frontend - Unit Selector (Low Risk)

**Objective**: Add dropdown to select unit, persist in localStorage

**Changes**:
1. Add `<select id="unit-selector">` to `index.html` header area
2. Add JavaScript:
   - Populate dropdown with 9 units
   - On change, save to localStorage, trigger statement load
   - On page load, restore selection from localStorage

**Verification**: Select unit, refresh page, selection persists

---

### Phase 5: Frontend - My Account Section (Medium Risk)

**Objective**: Display statement data in new dashboard section

**Changes**:
1. Add HTML section structure to `index.html`:
   - Prior year summary card
   - Current year summary card
   - Payment guidance card
   - Recent payments table
2. Add `renderMyAccount(data)` to `app.js`
3. Add `loadStatement(unit)` to fetch from API
4. Add CSS for new section layout

**Verification**: Statement displays correctly with all fields populated

---

### Phase 6: Edge Cases & Polish (Low Risk)

**Objective**: Handle special cases and improve UX

**Changes**:
1. Handle "no prior year data" state
2. Handle "budget not locked" warning
3. Handle "paid in full" / "credit balance" states
4. December special message
5. Loading/skeleton states
6. Responsive styling for mobile

**Verification**: All edge case scenarios display appropriate messages

---

## Testing Strategy

### Unit Tests (Backend)

```python
def test_carryover_calculation():
    """Verify carryover formula: budget + past_due - paid"""
    # Unit with $3960 budget, $0 past due, $3800 paid = $160 carryover

def test_carryover_preserves_manual():
    """Manual entries should not be overwritten"""

def test_statement_response_structure():
    """Verify all required fields present in API response"""

def test_months_remaining_calculation():
    """January=12, December=1"""
```

### Manual Testing

1. **Happy path**: Select unit, see correct statement
2. **Carryover accuracy**: Compare auto-calculated vs manual calculation for each unit
3. **Credit balance**: Test unit that overpaid shows credit correctly
4. **No prior data**: New unit with no history shows appropriate message
5. **Budget not locked**: Preliminary warning displays

---

## Deployment Plan

1. **Build**: `sam build`
2. **Deploy**: `sam deploy`
3. **Database migration**: Run ALTER TABLE (one-time)
4. **Smoke test**: Verify API responds, frontend loads
5. **Functional test**: Test each user story

---

## Rollback Plan

If issues are discovered:

1. **Backend**: Revert to previous Lambda version via AWS Console
2. **Frontend**: Revert S3 files from previous commit
3. **Database**: `auto_calculated` column can remain (backward compatible)

---

## Success Metrics

- [ ] Statement loads in < 3 seconds
- [ ] All 9 units have accurate carryover calculations
- [ ] Manual verification matches auto-calculation
- [ ] No console errors in frontend
- [ ] Works on mobile viewport
