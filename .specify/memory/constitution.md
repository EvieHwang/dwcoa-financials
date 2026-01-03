# DWCOA Financials Constitution

This document establishes the foundational architectural principles, design philosophy, and decision-making framework for the DWCOA Financials project.

## Project Mission

Build a simple, maintainable financial management tool for the Denny Way Condo Owners Association that automates transaction categorization, tracks budgets with proper timing, manages dues receivables by unit, and generates clear financial reports for residents.

## Architectural Principles

### 1. Simplicity First

**Rationale**: This is a personal/small-organization tool. Complexity is the enemy.

**Implementation**:
- File-based data storage (JSON/SQLite) over managed databases
- Static hosting where possible (S3 + CloudFront)
- Minimal infrastructure to maintain
- No over-engineering for hypothetical scale

**Trade-offs Accepted**:
- Not designed for multi-user concurrent editing
- Manual backup responsibility
- Limited to small data volumes (hundreds of transactions/year)

### 2. Serverless When Dynamic

**Rationale**: Pay only for what you use, zero server maintenance

**Implementation**:
- AWS Lambda for any server-side processing
- API Gateway for API endpoints
- S3 for static frontend hosting
- CloudFront for CDN and HTTPS

**Cost Guardrails**:
- No always-on compute
- No provisioned concurrency
- Cold starts are acceptable
- Target: < $5/month AWS costs

### 3. Claude API for Intelligence

**Rationale**: Leverage AI for transaction categorization without building complex rules

**Implementation**:
- Claude API (Haiku) for auto-categorizing transactions
- Simple rules engine for obvious matches first (reduce API calls)
- Baked-in categorization prompt (not user-editable via UI)
- Human review queue for low-confidence items

**Cost Guardrails**:
- Use Claude Haiku (cheapest model)
- Rules engine first, API second
- Learn patterns to reduce future API calls

### 4. Password-Protected Web Access

**Rationale**: Share with condo residents without exposing to public internet

**Implementation**:
- Two-tier password system: Admin and Board (view-only)
- Simple password protection (not full auth system)
- No user accounts or role-based access needed

**Trade-offs Accepted**:
- Shared passwords (not per-user)
- Not suitable for highly sensitive data
- Trust-based access model

### 5. The Dashboard IS the Report

**Rationale**: Single source of truth, no separate report generation

**Implementation**:
- Dashboard designed to be print-friendly (one page)
- Browser print = the report
- PDF download captures dashboard state
- No separate report formatting logic

### 6. Data Portability

**Rationale**: Treasurer role rotates; data must be transferable

**Implementation**:
- CSV as the master data format
- Full file replacement workflow (not incremental)
- All data downloadable at any time
- No proprietary formats

## Data Principles

### Transaction Model
- Full file replacement on each upload
- App enriches CSV with categorization columns
- Downloaded file includes app-added columns
- Categories preserved from upload where populated

### Budget Timing
- Three patterns only: Monthly, Quarterly, Annual
- YTD budget calculated based on pattern
- No complex seasonal or custom patterns

### Account Handling
- Three accounts: Savings (income), Checking (expenses), Reserve Fund
- Internal transfers excluded from budget reporting
- Total cash = sum of all three account balances

### Dues Tracking
- Unit-centric, not year-centric
- Outstanding = Expected - Paid (regardless of year)
- Ownership percentages are static

## Development Principles

### Specification-Driven
- Features start with specs in `/specs`
- Specs define requirements before implementation
- Implementation follows specs; deviations require spec updates

### Test Coverage
- Core business logic must have tests
- Financial calculations especially must be tested
- UI can have lighter test coverage

### Incremental Delivery
- Each user story is independently valuable
- MVP first, then iterate

## Technology Constraints

### Must Use
- Python 3.12+ for backend
- AWS for hosting (existing account)
- Claude API for AI features

### Prefer
- React or vanilla JS for frontend
- SQLite or JSON for data storage
- AWS SAM for deployment
- reportlab or similar for PDF

### Avoid
- Heavy frameworks (Django, etc.)
- Managed databases (RDS, DynamoDB for primary storage)
- Complex build systems
- Dependencies with large footprints

## Success Metrics

- Treasurer can import and review transactions in < 10 minutes
- Auto-categorization achieves 80%+ accuracy
- Dashboard loads in < 3 seconds
- Monthly AWS costs < $5
- Board members can access with just a password

## Revision History

- **2026-01-03**: Initial constitution established
