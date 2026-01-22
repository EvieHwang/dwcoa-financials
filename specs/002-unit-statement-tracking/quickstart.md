# Quickstart: Unit Statement Tracking

## Prerequisites

- Python 3.12+
- Node.js (for local testing if needed)
- AWS SAM CLI
- Access to AWS account with deployed DWCOA stack

## Local Development Setup

1. **Clone and checkout feature branch**:
   ```bash
   git checkout feature/002-unit-statement-tracking
   ```

2. **Install Python dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Run tests**:
   ```bash
   pytest
   ```

## Implementation Order

Follow this sequence to build the feature incrementally:

### Phase 1: Database Migration
1. Add `auto_calculated` column to `unit_past_dues` table
2. Run migration on deployed database

### Phase 2: Backend API
1. Create `backend/app/routes/statement.py` with:
   - `get_statement(unit, year)` - main statement endpoint
   - `get_payment_history(unit, year)` - full history endpoint
2. Add helper functions to `database.py`:
   - `get_unit_statement_data()`
   - `get_unit_payments()`
3. Wire up routes in `main.py`
4. Modify `budgets.py` to call carryover calculation on lock

### Phase 3: Frontend
1. Add unit selector dropdown to `index.html`
2. Add My Account section HTML structure
3. Add JavaScript in `app.js`:
   - `loadStatement(unit)` - fetch and render
   - `renderMyAccount(data)` - display logic
   - localStorage handling for unit persistence
4. Add CSS styles for new section

### Phase 4: Testing & Deployment
1. Manual testing with real data
2. Verify carryover calculations match manual verification
3. Deploy with `sam build && sam deploy`

## Key Files to Modify

| File | Changes |
|------|---------|
| `backend/sql/schema.sql` | Add `auto_calculated` column |
| `backend/app/routes/statement.py` | **NEW** - statement endpoints |
| `backend/app/services/database.py` | Add statement query functions |
| `backend/app/routes/budgets.py` | Add carryover calculation on lock |
| `backend/app/main.py` | Add statement routes |
| `frontend/index.html` | Add unit selector, My Account section |
| `frontend/app.js` | Add statement fetching/rendering |
| `frontend/styles.css` | Add My Account styles |

## Testing Checklist

- [ ] Select unit from dropdown, see statement populated
- [ ] Refresh page, selected unit persists
- [ ] Prior year shows correct budgeted vs paid
- [ ] Current year shows correct total due and remaining
- [ ] Payment guidance shows reasonable monthly amount
- [ ] Recent payments list appears with dates/amounts
- [ ] Lock budget triggers carryover calculation
- [ ] Manual past due entries are not overwritten
- [ ] Credit balances display correctly (negative amounts)

## API Testing

```bash
# Get statement for unit 201
curl -H "Authorization: Bearer $TOKEN" \
  "https://your-api.com/api/statement/201"

# Get full payment history
curl -H "Authorization: Bearer $TOKEN" \
  "https://your-api.com/api/statement/201/payments?year=2026"

# Lock budget and trigger carryover
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"locked": true}' \
  "https://your-api.com/api/budgets/lock/2026"
```

## Troubleshooting

**Statement shows $0 annual dues**:
- Check if current year budget exists
- Verify budget is not empty (run `/api/budgets?year=2026`)

**Carryover not calculating**:
- Ensure prior year has locked budget with data
- Check `unit_past_dues` table for existing manual entries

**Unit selector not persisting**:
- Check browser localStorage is enabled
- Look for `selectedUnit` key in browser dev tools

**Payment history empty but payments exist**:
- Verify transactions are categorized as "Dues {unit}" (e.g., "Dues 201")
- Check category name matches exactly
