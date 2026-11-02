# FaceAttendance

FaceAttendance is an in-progress, privacy-aware employee attendance project. Phase 1 provides a small Flask and SQLite foundation for employee records and manual daily attendance; it does **not** provide face recognition or production-ready attendance management.

## What is implemented and verified

- Flask application factory and local SQLite configuration.
- SQLAlchemy `Employee` and `Attendance` models, including one attendance record per employee per calendar day.
- Server-rendered dashboard and employee listing, registration, editing, and deactivation pages.
- Manual attendance service with active-employee and duplicate-day protection.
- Twelve pytest tests covering application startup/configuration, employee validation/flows, the employee-attendance relationship, duplicate prevention, inactive employees, and a foreign-key constraint.

Run the verified foundation locally after installing the dependencies:

```powershell
.\.venv\Scripts\Activate.ps1
python run.py
```

Open `http://127.0.0.1:5000`. The local database is created in the ignored `instance/` directory.

## Deliberately not implemented

- Administrator authentication, roles, CSRF protection, migrations, departments, shifts, policy calculations, reports, exports, and audit logs.
- Camera capture, biometric enrolment, biometric storage, face recognition, liveness checks, model evaluation, or an attendance kiosk.
- Deployment hardening and production configuration.

The existing OpenCV/LBPH Python scripts are **legacy prototype code** retained unchanged for learning and comparison. They are not part of the Flask application and must not be treated as a reliable attendance solution. The preserved image dataset is a small celebrity collection with documented quality and provenance limitations; it is excluded from Git and is unsuitable for employee-attendance evaluation.

## Recognition and data boundary

No face dataset, pretrained model weight, biometric template, employee photograph, or recognition benchmark has been downloaded, run, or evaluated for this Flask foundation. Any future pretrained ArcFace-style evaluation remains non-commercial portfolio research only, pending model-weight licence approval. Public benchmarks and consented employee evaluation must remain separate.

## Documentation

| Document | Purpose |
| --- | --- |
| [PROJECT_AUDIT.md](PROJECT_AUDIT.md) | Audit of the legacy prototype and its risks. |
| [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) | Current architecture and future security boundaries. |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Proposed full relational schema. |
| [DATASET_QUALITY_REPORT.md](DATASET_QUALITY_REPORT.md) | Read-only audit of the excluded legacy dataset. |
| [PUBLIC_DATASET_RESEARCH.md](PUBLIC_DATASET_RESEARCH.md) | Official-source dataset/model research and approval gates. |
| [RECOGNITION_EVALUATION.md](RECOGNITION_EVALUATION.md) | Evaluation methodology and recognition limitations. |
| [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) | Implementation milestones. |
| [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) | Local setup instructions. |
| [TESTING.md](TESTING.md) | Verified and planned tests. |

## Public-repository policy

This repository must never include employee photographs, biometric templates, downloaded face datasets, model weights, local databases, attendance records/exports, credentials, secrets, or local environment files. See [`.gitignore`](.gitignore) before adding files.
