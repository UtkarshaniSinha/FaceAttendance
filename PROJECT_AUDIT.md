# Project Audit â€” Employee Face Recognition Attendance System

**Audit date:** 2 November 2026
**Scope:** Phase 1 only. No existing application code, model, dataset, or attendance data was changed.

## Executive summary

This repository is an early face-recognition prototype, not yet an attendance-management application. It can train an OpenCV LBPH recognizer from a small downloaded celebrity-image dataset and attempt to identify faces from a webcam. It has no employee records, login, database, web interface, configurable attendance rules, reports, or automated tests.

The prototype is useful as a learning experiment, but it is not suitable for real employee attendance in its present form. In particular, the current data is public celebrity imagery rather than consenting employee data, and the recognition approach has not been evaluated against realistic unknown faces, lighting, pose, or spoofing attempts.

## Existing project structure

```text
FaceAttendance/
â”œâ”€â”€ .idea/                         # IDE settings (six files)
â”œâ”€â”€ attendance.csv/                # Empty directory; expected CSV is not present
â”œâ”€â”€ dataset/                       # 140 JPEGs: seven identities Ã— 20 images
â”‚   â”œâ”€â”€ Alejandro_Toledo/
â”‚   â”œâ”€â”€ Alvaro_Uribe/
â”‚   â”œâ”€â”€ Amelie_Mauresmo/
â”‚   â”œâ”€â”€ Andre_Agassi/
â”‚   â”œâ”€â”€ Angelina_Jolie/
â”‚   â”œâ”€â”€ Ariel_Sharon/
â”‚   â””â”€â”€ Arnold_Schwarzenegger/
â”œâ”€â”€ recognize.py/                  # Empty directory, despite its file-like name
â”œâ”€â”€ train.py/                      # Empty directory, despite its file-like name
â”œâ”€â”€ download_dataset.py
â”œâ”€â”€ recognize_attendance.py
â”œâ”€â”€ test_dataset_faces.py
â”œâ”€â”€ test_photo.py
â”œâ”€â”€ train model.py
â”œâ”€â”€ train model v2.py
â”œâ”€â”€ train model v3.py
â”œâ”€â”€ labels.pickle                  # Serialized LBPH label mapping
â””â”€â”€ trainer.yml                    # 16 MB trained LBPH model
```

No Git repository was detected in this folder. There is no `README.md`, `requirements.txt`, `.gitignore`, configuration file, database, application package, or test suite.

## Current implementation

| Component | What it does | Status |
| --- | --- | --- |
| `download_dataset.py` | Downloads LFW data using scikit-learn and saves up to 20 grayscale celebrity images for seven identities. | Implemented prototype utility |
| `train model.py` | Detects faces with Haar Cascade and trains OpenCV LBPH on detected face regions. | Older training experiment |
| `train model v2.py`, `train model v3.py` | Resizes every source image to 200Ã—200 and trains LBPH without detecting/cropping faces. | Implemented, but duplicates each other and is technically inconsistent with the older script |
| `recognize_attendance.py` | Opens webcam 0, detects faces with Haar Cascade, predicts with LBPH, overlays a label, and appends an unseen name to an in-memory/DataFrame CSV list. | Partly implemented proof of concept |
| `test_photo.py`, `test_dataset_faces.py` | Print predictions for images in the same dataset used for training. | Manual diagnostic scripts; not automated tests |

### Recognition flow

`webcam frame â†’ grayscale â†’ Haar Cascade face detection â†’ resize face to 200Ã—200 â†’ LBPH prediction â†’ threshold check â†’ overlay name â†’ append name/time to CSV`

LBPH is a lightweight, offline OpenCV recognizer. It is reasonable for learning and a tightly controlled demonstration with a small, consented dataset. It is not sufficiently robust by itself for a professional attendance product: it is sensitive to lighting, pose, image quality, camera differences, and presentation attacks.

## Technologies found

- Python (source code is Python, but no usable interpreter is configured on this computer)
- OpenCV, including the contrib `cv2.face` module for LBPH and Haar Cascade detection
- NumPy and Pillow
- pandas for CSV handling
- scikit-learn for the LFW downloader
- Pickle/YAML model artifacts

The source imports do not pin versions. `cv2.face` requires an OpenCV *contrib* build; a basic `opencv-python` install would not work.

## Implemented versus missing features

### Present

- Dataset download utility.
- Simple local model training.
- Webcam capture and face-detection loop.
- Confidence-thresholded label display.
- Basic unknown-face label.
- Very basic name/time CSV write attempt.

### Missing or incomplete

- Employee creation, ID generation, editing, deactivation, profiles, and search.
- Consent collection, biometric retention policy, deletion workflow, and audit log.
- Face-registration workflow, image-quality checks, duplicate-registration detection, and multi-sample capture.
- Reliable recognition evaluation, calibration, multi-frame confirmation, and unknown-face validation.
- Check-in/check-out state, daily reset, shifts, grace periods, late/early-departure logic, or duplicate cooldown.
- Database schema, constraints, transactions, migrations, and backups.
- Admin authentication, password hashing, sessions, roles, input validation, and access controls.
- Dashboard, attendance history, search/filtering, CSV/Excel/PDF reporting, and responsive UI.
- Liveness/anti-spoof controls and camera-health handling.
- Dependency management, environment configuration, setup instructions, `.gitignore`, Git repository, and automated tests.

## Bugs, risks, and technical debt

1. **Attendance never resets daily.** `if name not in attendance_df["Name"]` blocks every later attendance event as long as the CSV is retained. It cannot support check-out or next-day check-in.
2. **No actual attendance CSV exists.** `attendance.csv` is currently a directory, while the program expects it to be a file. A CSV write to that path will fail with an `IsADirectoryError`, which the code does not catch.
3. **No database-level duplicate prevention.** CSV reads/writes are not transactional and are unsafe for concurrent use or recovery after interruption.
4. **Inconsistent training pipelines.** The first trainer uses detected face regions of varying dimensions; versions 2/3 train on whole resized source images. Recognition crops a face then resizes it. The model artifact does not state which trainer produced it.
5. **No face alignment or quality validation.** Blurry, tiny, poorly lit, profile, or multi-face data can be trained/recognized without checks.
6. **Thresholds are arbitrary and inconsistent.** Recognition uses 50 while test scripts use 100. LBPH distance is not a probability, and no measured false-accept/false-reject evaluation supports either number.
7. **Invalid test methodology.** Both diagnostic scripts test on the exact dataset used for training, so their output cannot measure generalization. They are not test cases with assertions.
8. **Potential runtime crashes.** A missing/invalid model, labels file, cascade, camera, or label ID is not handled. `labels[id_]` can raise `KeyError`.
9. **Haar Cascade limitations.** It is an older detector with weak performance under non-frontal pose and difficult lighting; it may also detect multiple faces without an attendance safety policy.
10. **Privacy and licensing risk.** The committed dataset consists of identifiable real people and should not be used as employee biometric training data. The `.pickle` file is also unsafe to load if it has been replaced by an untrusted party.
11. **No anti-spoofing.** A photograph or screen replay may be accepted. Basic motion/blink checks, if later added, must not be presented as strong protection.
12. **Repository hygiene gaps.** Model, image data, and IDE settings are currently present; a future public repository must exclude real biometric samples, production models tied to them, databases, secrets, virtual environments, and caches.
13. **Environment is not runnable here.** `python` is not on `PATH`; `py.exe` exists but reports no default Python runtime. Therefore no runtime import, model, or webcam test was performed.

## Recommended architecture (approval required before implementation)

Keep Python and OpenCV. Evolve the prototype incrementally into a modular Flask application with a local SQLite database for development and a clear PostgreSQL production path.

```text
Browser admin UI / kiosk UI
            â”‚
       Flask application
 â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
 Employees  Attendance  Reports/Auth
            â”‚
  Recognition service (OpenCV + approved recognizer)
            â”‚
 SQLite (development) â†’ PostgreSQL (deployment)
```

### Recommended choices

| Concern | Recommendation | Reason |
| --- | --- | --- |
| Backend/UI | Flask + server-rendered Jinja templates + small vanilla JavaScript | Simpler to learn, deploy, and maintain than a separate SPA/API for this project size. |
| Database | SQLAlchemy with SQLite locally; PostgreSQL when deployed | Gives strong constraints and migrations without making first setup difficult. |
| Recognition | Retain OpenCV as the camera/image-processing layer; add a tested embedding-based recognizer only after a measured comparison | More robust than LBPH under normal variation, but adds model/dependency complexity. Do not replace the current pipeline until approved. |
| Detection | OpenCV DNN/modern detector behind a `FaceDetector` interface | More reliable than Haar Cascade while preserving the ability to fall back or compare. |
| Authentication | Werkzeug password hashes, Flask sessions, CSRF protection, role checks | A practical secure baseline with no plaintext passwords. |
| Reporting | pandas/openpyxl for CSV/XLSX; ReportLab for PDF | Fits the specified export formats and keeps reports generated server-side. |
| Configuration | `.env` locally plus validated environment settings | Keeps secrets, database URLs, and thresholds out of source control. |

This intentionally does **not** claim to make biometric attendance suitable for high-security use. The kiosk should show consent information; capture only necessary templates/samples; restrict administrator access; support deletion; and keep an audit trail.

## Proposed database design

Use UTC timestamps in storage and an organization timezone setting for display/policy calculations.

| Table | Key fields and rules |
| --- | --- |
| `administrators` | `id`, unique `email`, `password_hash`, `role`, `is_active`, timestamps. |
| `departments` | `id`, unique `name`, `is_active`. |
| `shifts` | `id`, `name`, scheduled check-in/out times, grace/minimum-work minutes, active flag. |
| `attendance_policies` | `id`, organization/shift scope, duplicate-cooldown seconds, allowed event rules, recognition threshold/version, effective dates. |
| `employees` | UUID/public employee code, department/shift foreign keys, name/contact fields, active flag, consent timestamp/version, created/updated timestamps. Unique employee code. |
| `biometric_templates` | `id`, employee FK, encrypted or protected template blob/path, model version, quality score, created/revoked timestamps. Do not expose through normal routes. |
| `recognition_events` | `id`, employee FK nullable for unknowns, time, confidence/distance, model version, camera ID, decision/reason. Retain only what policy requires. |
| `attendance_records` | `id`, employee FK, local attendance date, shift FK, check-in/out UTC times, status, late/early minutes, source event FKs, notes. Unique `(employee_id, attendance_date, shift_id)`. |
| `audit_logs` | actor, action, target type/id, timestamp, minimal metadata. |
| `app_settings` | organization name, timezone, retention durations, configured defaults. |

Indexes should cover employee code/name, active employees, events by time/employee, and attendance by date/employee/department. Attendance creation must occur in a database transaction; the unique constraint is the final protection against duplicate daily records.

## Prioritised roadmap

1. **Foundation:** obtain a supported Python runtime, create Git repository/checkpoint, dependency specification, `.gitignore`, environment template, and documentation.
2. **Domain and data:** implement the database, migrations, authentication, employee/department/shift management, consent and deletion controls.
3. **Registration:** consent-gated sample capture, quality checks, template storage, duplicate safeguards, and an admin review path.
4. **Recognition evaluation:** build a consented synthetic/demo test set; compare current LBPH against an embedding approach; select/calibrate thresholds using held-out known and unknown samples. Obtain approval before replacement.
5. **Attendance engine:** implement deterministic check-in/out, shifts, late/early calculations, cooldown, and database-enforced duplicate prevention.
6. **User experience:** build dashboard, kiosk feedback, history/filtering, and recoverable camera errors.
7. **Reports and hardening:** export CSV/XLSX/PDF, retention jobs, audits, access controls, camera interruption handling, and documented spoofing limits.
8. **Verification and release:** automated unit/integration tests, manual hardware test matrix, installation guide, screenshots with synthetic data, and GitHub readiness review.

## Audit verification performed

- Enumerated the repository structure and counted the dataset: seven folders, 140 images total.
- Read all seven Python source files and inspected the generated model/label artifact metadata.
- Checked for Git metadata: this directory is not currently a Git repository.
- Attempted to identify the Python environment. `python` was unavailable; the Windows Python launcher exists but has no installed/default runtime.
- No webcam, download, training, recognition, or runtime test was run because the interpreter is unavailable and Phase 1 excludes implementation changes.

## Approval decision needed

Before Phase 2, please confirm whether you approve the proposed Flask + SQLAlchemy + SQLite/PostgreSQL architecture and the plan to **evaluate, then likely replace** the LBPH recognition model with a modern embedding-based recognizer. The existing prototype files and artifacts will be preserved during that work unless you explicitly approve their removal.

## Direction update â€” 2 November 2026

The approved portfolio direction is now a pretrained ArcFace-style embedding architecture rather than training a large network from scratch. The detailed dataset/model access and licensing assessment is in `PUBLIC_DATASET_RESEARCH.md`. This does not change the audit finding that the existing 140-image celebrity subset is a legacy prototype artifact and unsuitable for employee evaluation.
