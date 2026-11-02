# Employee Face Recognition Attendance Management System

> **Project status: planning and GitHub preparation.** The web application has not been implemented and no recognition model has been evaluated in this repository yet.

This project is being developed into a privacy-aware employee attendance system. The planned application will use a webcam to capture a face, generate a biometric embedding with an approved pretrained recognition model, apply configurable attendance rules, and provide an administrator dashboard and reports.

## What exists today

This repository preserves an early OpenCV/LBPH learning prototype. It contains scripts to download a small legacy face dataset containing seven celebrity identities (140 images), train an LBPH model, make webcam predictions, and attempt basic CSV attendance logging.

These scripts are **legacy prototype code**, not the planned application. They are retained for learning and comparison, but the related dataset/model artefacts are excluded from Git because they contain biometric material. Their limitations are documented in [PROJECT_AUDIT.md](PROJECT_AUDIT.md) and [DATASET_QUALITY_REPORT.md](DATASET_QUALITY_REPORT.md).

## Planned architecture

- **Computer vision:** Python, OpenCV, and a replaceable ArcFace-style embedding adapter.
- **Backend:** Flask with REST endpoints and server-rendered administrator pages.
- **Data:** SQLAlchemy; SQLite for local development and PostgreSQL for deployment.
- **Frontend:** HTML, CSS, JavaScript, and charts for attendance analytics.
- **Quality:** pytest, documented evaluation, and Docker preparation where appropriate.

The research pipeline is planned as: face image -> detection and alignment -> normalized embedding -> cosine-similarity comparison -> calibrated known/unknown decision -> policy-controlled attendance action.

## Licence, privacy, and scope

- The preferred ArcFace-style research option uses public pretrained model weights only after their terms are approved. InsightFace code is MIT, but its public pretrained weights are non-commercial research only.
- Public verification benchmarks and employee attendance evaluation are separate. Actual employees must be enrolled with consent through the future application.
- This repository must never contain employee photographs, biometric templates, downloaded public face datasets, model weights, local databases, attendance exports, credentials, or secrets.
- Liveness/presentation-attack detection is optional and not implemented. Basic motion/blink checks are not strong spoofing protection.

## Documentation

| Document | Purpose |
| --- | --- |
| [PROJECT_AUDIT.md](PROJECT_AUDIT.md) | Audit of the original prototype and its risks. |
| [PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) | Planned system structure, security, and deployment design. |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Proposed relational schema and attendance-rule model. |
| [DATASET_QUALITY_REPORT.md](DATASET_QUALITY_REPORT.md) | Read-only audit of the preserved legacy dataset. |
| [PUBLIC_DATASET_RESEARCH.md](PUBLIC_DATASET_RESEARCH.md) | Official-source dataset/model research and licence gates. |
| [RECOGNITION_EVALUATION.md](RECOGNITION_EVALUATION.md) | Evaluation methodology and recognition limitations. |
| [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) | Phased plan and learning objectives. |
| [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) | Planned local setup; currently untested. |
| [TESTING.md](TESTING.md) | Test strategy and honest test status. |
| [CHANGELOG.md](CHANGELOG.md) | Human-readable project history. |

## Setup status

A supported Python runtime is not configured in the audited workspace, so installation commands and dependencies have not been executed here. See [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for the planned, explicitly untested setup path.

## Repository policy

This public repository is documentation- and source-code-ready only. It deliberately excludes all biometric assets and runtime data. Do not add such files without a documented consent, retention, and licence review.
