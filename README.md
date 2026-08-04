# GateGuard backend (Django + DRF)

## Setup
```bash
python -m venv venv
source venv/bin/activate   # venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env       # fill in DATABASE_URL (Neon) and Cloudinary keys
python manage.py migrate
python manage.py seed_demo   # creates demo users + PCs, one flagged stolen
python manage.py runserver
```

## Demo accounts (created by seed_demo, password Passw0rd! for all)
- superadmin — Super Admin
- admin_cs / admin_eng / admin_bus — DPT Admins
- guard1 — Guard
- emp_cs_1, emp_cs_2, emp_cs_3, emp_eng_1... — Employees (3 per department)
- CS-PC-003 is pre-flagged STOLEN for the demo

## Key endpoints
| Method | URL | Who | Purpose |
|---|---|---|---|
| POST | /api/auth/login/ | anyone | Get JWT access/refresh + role |
| POST | /api/auth/token/refresh/ | anyone | Refresh access token |
| POST | /api/auth/users/create/ | Super Admin, DPT Admin | Create users |
| GET | /api/dpts/ | Super Admin | List/manage departments |
| GET/POST | /api/devices/ | Super Admin, DPT Admin | CRUD PCs (QR auto-generated on create) |
| GET | /api/devices/my-devices/ | Employee | View own PCs + QR download link |
| GET | /api/devices/lookup/<qr_token>/ | Guard | Scan result: owner + PC info + stolen_alert |
| POST | /api/scans/ | Guard | Submit approve/deny; auto-flags if PC is stolen |
| GET | /api/scans/logs/ | Super Admin, DPT Admin | Audit trail |
| GET | /guard-scanner/ | Guard (browser) | Mobile-friendly QR scanner page |

## Guard scanner
Open `/guard-scanner/` on a guard's phone browser. It logs in, opens the
camera, scans a QR, shows the owner + a stolen-device warning if flagged,
and lets the guard approve or deny in one tap.

## Notes
- Images (QR codes + scan evidence photos) upload straight to Cloudinary —
  configured via CLOUDINARY_* env vars, no extra code needed.
- DB is Neon Postgres via DATABASE_URL — sslmode=require is applied
  automatically for postgres URLs.
- Verified end-to-end locally: login for all 4 roles, employee device view,
  guard scan + approve, and the stolen-device auto-flag override.
