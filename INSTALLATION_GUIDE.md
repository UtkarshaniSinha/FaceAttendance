# Installation Guide

## Status

These are planned setup instructions for the future Flask application. They are **not yet tested in this workspace** because Windows has no usable Python runtime configured and Phase 3 implementation has not started.

## Expected prerequisites

- Windows, macOS, or Linux.
- Python 3.11 or later.
- Git.
- A webcam for later recognition experiments.
- Optional: PostgreSQL and Docker for later deployment work.

## Planned local setup

```powershell
git clone <your-public-repository-url>
cd FaceAttendance
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set a new private `SECRET_KEY` in `.env`; never commit that file. SQLite is the planned default local database. Migrations, a Flask entry point, and runnable server commands do not exist yet, so no `flask run` command is documented as working.

## Future model and data setup

Do not download face datasets or pretrained model weights merely to follow this guide. Each download needs approval of its official licence, intended use, storage location, and exclusion from Git. See `PUBLIC_DATASET_RESEARCH.md` and `RECOGNITION_EVALUATION.md`.

## Current workspace limitation

The `py` launcher exists but reports no default Python installation, and `python` is not on `PATH`. After installing Python, confirm it with:

```powershell
py -3.11 --version
```
