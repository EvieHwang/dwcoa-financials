# DWCOA Financial Dashboard

A serverless financial management application for the Denny Way Condo Owners Association. Built with Python/AWS Lambda backend and vanilla JavaScript frontend.

## Features

- **Transaction Management**: Upload bank CSV exports, auto-categorize transactions using rules engine and Claude AI
- **Budget Tracking**: Set annual budgets with timing patterns (monthly, quarterly, annual) for accurate YTD calculations
- **Dues Tracking**: Track dues payments by unit based on ownership percentages
- **Reserve Fund Monitoring**: Track contributions and expenses with YTD net change
- **Financial Reports**: View dashboard, download PDF reports, export transaction CSV
- **Date Snapshots**: View financial state as of any historical date
- **Role-Based Access**: Admin (full access) and Homeowner (view-only) roles

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   CloudFront    │────▶│   S3 (Frontend) │     │   S3 (Data)     │
│   Distribution  │     │   Static Files  │     │   SQLite DB     │
└────────┬────────┘     └─────────────────┘     └────────▲────────┘
         │                                               │
         │ /api/*                                        │
         ▼                                               │
┌─────────────────┐     ┌─────────────────┐              │
│   API Gateway   │────▶│     Lambda      │──────────────┘
│   (HTTP API)    │     │   (Python 3.12) │
└─────────────────┘     └─────────────────┘
```

- **Frontend**: Vanilla HTML/CSS/JavaScript hosted on S3
- **Backend**: Python 3.12 Lambda function with SQLite database stored in S3
- **Infrastructure**: AWS SAM for deployment, CloudFront for CDN and routing

## Prerequisites

- Python 3.12+
- AWS CLI configured with appropriate credentials
- AWS SAM CLI
- Node.js (for local development only)

## Local Development

```bash
# Install Python dependencies
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest

# Build SAM application
sam build

# Start local API
sam local start-api
```

## Deployment

```bash
# Build the application
sam build

# Deploy (first time - guided)
sam deploy --guided

# Deploy (subsequent)
sam deploy

# Sync frontend to S3
aws s3 sync frontend/ s3://dwcoa-frontend-{ACCOUNT_ID}

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id {DIST_ID} --paths "/*"
```

## Configuration

The following parameters are configured via AWS Systems Manager Parameter Store or SAM deploy:

| Parameter | Description |
|-----------|-------------|
| `AdminPasswordHash` | Bcrypt hash for admin login |
| `BoardPasswordHash` | Bcrypt hash for homeowner login |
| `AnthropicApiKey` | API key for Claude auto-categorization |
| `JwtSecret` | Secret for signing authentication tokens |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py           # Lambda handler and routing
│   │   ├── routes/           # API route handlers
│   │   │   ├── auth.py       # Authentication
│   │   │   ├── budgets.py    # Budget management
│   │   │   ├── categories.py # Category CRUD
│   │   │   ├── dashboard.py  # Dashboard data
│   │   │   ├── dues.py       # Dues tracking
│   │   │   ├── reports.py    # PDF generation
│   │   │   └── transactions.py
│   │   └── services/         # Business logic
│   │       ├── budget_calc.py
│   │       ├── csv_processor.py
│   │       ├── database.py
│   │       └── pdf_generator.py
│   ├── sql/
│   │   ├── schema.sql        # Database schema
│   │   ├── seed.sql          # Initial data
│   │   └── rules.sql         # Auto-categorization rules
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── specs/                    # Feature specifications
├── template.yaml             # SAM template
└── Makefile
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Authenticate user |
| GET | `/api/auth/verify` | Verify JWT token |
| GET | `/api/dashboard` | Get dashboard data |
| POST | `/api/transactions/upload` | Upload CSV file |
| GET | `/api/transactions/download` | Download transactions CSV |
| GET | `/api/reports/pdf` | Generate PDF report |
| GET | `/api/budgets` | List budgets for year |
| POST | `/api/budgets` | Create/update budget |
| POST | `/api/budgets/copy` | Copy budgets between years |
| GET | `/api/categories` | List categories |
| POST | `/api/categories` | Create category |
| PATCH | `/api/categories/{id}` | Update category |
| GET | `/api/review` | Get transactions needing review |

## License

Private - All rights reserved.

## Support

For questions or feature requests, contact the project maintainer.
