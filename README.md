
# Financial Rules Engine and Payroll Simulator

A backend application built with Django REST Framework and PostgreSQL to calculate payroll using configurable, versioned financial rules.

## Features

- REST API for payroll calculations
- Versioned financial rules with effective dates
- Decimal-based monetary calculations
- Idempotency keys to prevent duplicate payroll records on retries
- Conflict detection when a key is reused with a different request
- Audit logs for payroll calculation events
- Django Admin for inspecting payroll records and audit history
- PostgreSQL database with Docker Compose
- Automated tests

## Tech Stack

- Python 3.13
- Django 5.2
- Django REST Framework
- PostgreSQL 16
- Docker and Docker Compose
- pytest is not required; tests use Django's built-in test framework

## Prerequisites

- Docker Desktop
- Git

## Getting Started

1. Clone the repository:

   ```bash
   git clone <YOUR_GITHUB_REPOSITORY_URL>
   cd financial-rules-engine
   ```

2. Create a `.env` file in the project root:

   ```dotenv
   DB_NAME=payroll_db
   DB_USER=payroll_user
   DB_PASSWORD=replace_with_a_local_password
   DB_HOST=127.0.0.1
   DB_PORT=5432
   ```

3. Start the application:

   ```bash
   docker compose up --build -d
   ```

4. Create the demo financial rule:

   ```bash
   docker compose exec web python manage.py shell -c "from rules.models import FinancialRule; FinancialRule.objects.get_or_create(name='STANDARD_DEDUCTION', version=1, defaults={'effective_from': '2026-01-01', 'configuration': {'rate': '0.10'}, 'is_active': True})"
   ```

5. Create an admin account:

   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

6. Open the API and admin dashboard:

   - API: http://127.0.0.1:8000/api/payroll/calculate/
   - Admin: http://127.0.0.1:8000/admin/

## API Usage

### Calculate Payroll

`POST /api/payroll/calculate/`

Required header:

`Idempotency-Key: unique-request-key`

Example JSON body:

```json
{
  "employee_reference": "EMP-001",
  "pay_period_start": "2026-10-01",
  "pay_period_end": "2026-10-31",
  "gross_pay": "5000.00"
}
```

Example result with the demo 10% deduction rule:

- Gross pay: 5000.00
- Deductions: 500.00
- Net pay: 4500.00

The response includes the payroll record ID, calculated amounts, rule snapshot, and creation timestamp.

An identical retry with the same idempotency key reuses the existing record. Reusing the key with a different payload returns HTTP 409 Conflict.

## Run Tests

```bash
docker compose exec web python manage.py test payroll
```

The project currently has 19 automated tests passing against PostgreSQL.

## Stop the Application

```bash
docker compose down
```

To remove the Compose database volume and its data as well:

```bash
docker compose down -v
```

**Warning:** `docker compose down -v` permanently deletes the database data stored in that volume.

## Limitations

This is an educational portfolio project. The 10% deduction rule is fictional and must not be used for real payroll, tax, or regulatory calculations.
