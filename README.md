# 🗺️ Urban Incident Alert Map

[![DevSecOps](https://github.com/trannguyennee/DuAnGisMoi/actions/workflows/devsecops.yml/badge.svg)](https://github.com/trannguyennee/DuAnGisMoi/actions/workflows/devsecops.yml)
![Django](https://img.shields.io/badge/Django-5.2_LTS-092E20?logo=django&logoColor=white)
![PostGIS](https://img.shields.io/badge/PostGIS-3-336791?logo=postgresql&logoColor=white)
![Leaflet](https://img.shields.io/badge/Leaflet-1.9-199900?logo=leaflet&logoColor=white)

A WebGIS platform where residents report urban incidents (flooding, broken street lights, road hazards) on a live map, and police or support teams triage and resolve them from one shared view.

> **日本語：** 住民が冠水・街灯の故障・道路の危険などの都市トラブルを、位置情報と写真付きで地図上に通報できる WebGIS プラットフォームです。警察や支援チームは一つの地図上ですべての通報を客観的に把握し、対応状況を管理できます。

> **Tiếng Việt:** Ý tưởng xuất phát từ các trang web cầu cứu trên bản đồ trong mùa lũ. Người dân gửi phản ánh sự cố đô thị kèm vị trí và ảnh; cảnh sát và đơn vị hỗ trợ theo dõi mọi phản ánh trên cùng một bản đồ để xử lý khách quan hơn.

## Features

- 📍 **Report incidents** with map pin(s), address, description and photo — no account required
- 🔥 **Heatmaps** by status: pending · in progress · resolved
- 🧭 **Route to incident** (Leaflet Routing Machine) and distance tools (Turf.js)
- 📡 **Area-scan API** — PostGIS `distance_lte` query: every incident within *R* metres of a point
- 🛠️ **Admin dashboard** — approve / progress reports, lock or remove users, export CSV
- 📰 **City news feed** filtered from VnExpress RSS, emergency hotline directory, support tickets

## Tech stack

| Layer | Tech |
|---|---|
| Backend | Python 3.13, Django 5.2 LTS, GeoDjango, Gunicorn, WhiteNoise |
| Database | PostgreSQL + PostGIS (`PointField`, SRID 4326) |
| Frontend | Leaflet, Leaflet.heat, Leaflet Routing Machine, Turf.js, Bootstrap |
| Deploy | Railway |
| DevSecOps | GitHub Actions · gitleaks · bandit · pip-audit · Dependabot |

## 🔐 Security

This project went through a security review. What was found and fixed:

| Issue | Risk | Fix |
|---|---|---|
| `SECRET_KEY` hard-coded in `settings.py`, `DEBUG=True`, `ALLOWED_HOSTS=['*']` | Session forgery, stack traces leaked in production | All secrets from environment variables; `DEBUG` off by default; host allow-list; HSTS + secure cookies |
| Coordinates rendered with `\|safe` inside `<script>` | **Stored XSS** on the public map — any visitor could run JS in the admin's browser | Coordinates validated server-side and re-serialized as numbers only; template filter escapes output |
| Admin actions (delete user, delete report, lock user) via plain GET links | **CSRF** — a malicious link/image could make an admin delete accounts | POST-only + CSRF token; separate admin vs. owner delete routes |
| `?next=` redirect after login not validated | Open redirect (phishing) | `url_has_allowed_host_and_scheme` |
| Upload accepted any file type | HTML/script uploaded as "image" | Pillow content validation + 5 MB limit |
| CSV export public and unescaped | Data exposure, Excel formula injection | Staff-only + formula escaping |
| `db.sqlite3` (with user accounts), `__pycache__`, user uploads committed | Personal data leak | Removed from the repo, `.gitignore` hardened |
| Outdated Django, Pillow, lxml, sqlparse, soupsieve | 101 known vulnerabilities (pip-audit) | Upgraded; pip-audit now runs in CI |

Every push now goes through the [DevSecOps pipeline](.github/workflows/devsecops.yml): **secret scan → SAST → dependency audit → tests on PostGIS → `check --deploy`**. See [SECURITY.md](SECURITY.md).

## Run locally

Requirements: Python 3.13, PostgreSQL with the PostGIS extension (the Windows installer's StackBuilder includes PostGIS, GDAL and GEOS).

```bash
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # macOS/Linux: cp .env.example .env  — then fill it in
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

| Variable | Required | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | in production | Generate a new one, never commit it |
| `DJANGO_DEBUG` | no | `True` only for local development (default `False`) |
| `DATABASE_URL` | yes | e.g. `postgis://user:pass@localhost:5432/gis` |
| `DJANGO_ALLOWED_HOSTS` | no | Comma-separated; Railway's domain is added automatically |
| `POSTGRES_BIN` | Windows only | PostgreSQL `bin` folder containing GDAL/GEOS DLLs |

Run the security test suite:

```bash
python manage.py test maps
```

## Deploy on Railway

Set `DJANGO_SECRET_KEY` (and `DATABASE_URL` from the Railway PostGIS service) in the service's **Variables** tab. `RAILWAY_PUBLIC_DOMAIN` is picked up automatically for `ALLOWED_HOSTS` and CSRF.

## Team

Built as a team project at Ho Chi Minh City University of Natural Resources and Environment (HCMUNRE) — see [contributors](https://github.com/trannguyennee/DuAnGisMoi/graphs/contributors).
