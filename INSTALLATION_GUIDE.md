# Installation Guide

## Verified local foundation

The Phase 1 Flask foundation was verified with Python 3.12, Flask, Flask-SQLAlchemy, SQLite, and pytest on Windows. Camera and recognition functionality have not been implemented or tested.

## Prerequisites

- Python 3.11 or 3.12.
- Git (optional for local use).

### If Python is not installed on Windows

The audited workstation does not have a system Python exposed through `python` or `py`. Install the current 64-bit Python 3.12 release from the [official Windows downloads page](https://www.python.org/downloads/windows/). In the installer, select **Add python.exe to PATH** and install the Python launcher. Close and reopen PowerShell, then confirm with:

```powershell
py -3.12 --version
```

## Setup

```powershell
git clone <your-public-repository-url>
cd FaceAttendance
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python run.py
```

Then open `http://127.0.0.1:5000`. The application automatically creates `instance/face_attendance.db`; it is local runtime data and is ignored by Git.

Set a fresh private `SECRET_KEY` in `.env` before using any environment beyond local development. Never commit `.env`.

## Tests

```powershell
pytest -q
```

The current suite verifies only the Phase 1 foundation. It does not evaluate recognition accuracy, camera behaviour, security controls, or production deployment.

## Data and model restriction

Do not download datasets or pretrained model weights merely to follow this guide. Every such download needs separate approval of the official source, licence, intended use, storage location, and Git exclusion. See `PUBLIC_DATASET_RESEARCH.md` and `RECOGNITION_EVALUATION.md`.
