# Changelog

All noteworthy project milestones are recorded here in plain language. Dates use the project timezone (Asia/Kolkata).

## [Unreleased]

### 2026-11-03 — Phase 1 Flask and SQLite foundation

**What changed:** Implemented a local Flask application foundation with an application factory, SQLite configuration, employee and attendance models, employee management pages, a basic dashboard, and service-level duplicate-attendance rules.

**Verification:** `pytest -q` completed with **12 passed**. The application factory, SQLite database creation, and Python compilation checks also completed successfully. OpenCV contrib imports successfully and exposes `cv2.face`; no recognition pipeline was run.

**Important scope boundary:** This change does not implement authentication, biometric enrolment/storage, camera capture, face recognition, liveness, recognition evaluation, reports, or production hardening. The legacy dataset and LBPH prototype were not modified, downloaded, trained, or benchmarked.

**Git status:** The changes remain uncommitted and unpushed pending explicit review and approval.

### 2026-11-02 — Public-repository preparation

**What changed:** Added public-ready documentation and configuration templates, and prepared rules for excluding sensitive biometric and runtime material.

**Previous behaviour:** The project had planning documentation but no README, installation guide, testing guide, dependency file, safe environment example, or Git ignore rules.

**New behaviour:** The repository now explains its prototype status, planned architecture, setup limitations, testing status, and privacy boundaries. `.gitignore` protects datasets, model artefacts, biometric data, local databases, secrets, IDE settings, and temporary output from future publication.

**Files created:**

- `README.md`
- `INSTALLATION_GUIDE.md`
- `TESTING.md`
- `requirements.txt`
- `.env.example`
- `.gitignore`

**Files modified:**

- `CHANGELOG.md`
- `.gitignore`

**Files removed:** None. Existing prototype source, dataset, and model files remain locally preserved.

**Testing:** Documentation and ignore rules were reviewed. Dependencies and runtime functionality are explicitly untested because no usable Python runtime is configured and Phase 3 has not started.

**Current status:** A fresh local Git repository was initialised on the `main` branch after confirming the previous `.git` directory contained no metadata or history. No remote, commit, or push has been created.

### 2026-11-02 — Pretrained-model and public-dataset research plan

**What changed:** Added public-dataset research and incorporated a career-oriented pretrained ArcFace-style embedding direction into the architecture, evaluation plan, and roadmap.

**Previous behaviour:** The project proposed embeddings but did not identify a preferred learning workflow or distinguish code licences from public model-weight and dataset licences.

**New behaviour:** `PUBLIC_DATASET_RESEARCH.md` ranks official sources, records access/terms limitations, and recommends a replaceable pretrained embedding adapter for non-commercial portfolio research. The roadmap now makes data/model licence approval a prerequisite to model evaluation.

**Why this was changed:** It gives practical exposure to embeddings, cosine similarity, thresholds, FAR/FRR, and model integration without training a large neural network from scratch.

**Important licence finding:** InsightFace code is MIT, while its public pretrained model packs are non-commercial research only. Publicly available data or weights do not automatically grant commercial use.

**Files created:**

- `PUBLIC_DATASET_RESEARCH.md`

**Files modified:**

- `PROJECT_AUDIT.md`
- `PROJECT_ARCHITECTURE.md`
- `RECOGNITION_EVALUATION.md`
- `DEVELOPMENT_ROADMAP.md`
- `DATASET_QUALITY_REPORT.md`
- `CHANGELOG.md`

**Testing:** Official sources and original publications were researched. No dataset/model was downloaded, no terms were accepted, and no model was run.

**Current status:** Awaiting explicit dataset/model selection and licence approval. GitHub integration and Phase 3 remain paused.

### 2026-11-02 — Read-only dataset quality audit

**What changed:** Added a measurement-based audit of the existing face-image dataset and made dataset validation a required stage before recognition evaluation.

**Previous behaviour:** The project had a small celebrity-image dataset but no documented assessment of its resolution, exposure, detail, provenance limits, or suitability for attendance recognition.

**New behaviour:** `DATASET_QUALITY_REPORT.md` records 140 images across seven celebrity labels, all at 47×62 pixels. It documents brightness, clipping, sharpness-proxy, exact-duplicate results, limitations, and requirements for a consented replacement dataset. The recognition plan now explicitly forbids using this data for attendance benchmarks or deployment claims.

**Why this was changed:** Image quality and independent, consented capture sessions are necessary for a meaningful recognition evaluation. Enhancement alone cannot recover missing facial detail or create valid evaluation data.

**Files created:**

- `DATASET_QUALITY_REPORT.md`

**Files modified:**

- `RECOGNITION_EVALUATION.md`
- `DEVELOPMENT_ROADMAP.md`
- `CHANGELOG.md`

**Files removed or altered:** None. This was a read-only audit of the dataset; no image, label, model, or source file was trained, enhanced, moved, renamed, overwritten, or deleted.

**Testing:** A read-only image scan measured dimensions, grayscale brightness/contrast, clipped-pixel share, a comparative Laplacian sharpness proxy, file hashes, file counts, and JPEG properties. No recognition model was trained or benchmarked.

**Current status:** Dataset unsuitable for employee attendance development/evaluation. Replacement data collection and validation are planned but not started. Phase 3 and GitHub integration remain paused.

### 2026-11-02 — Phase 2 architecture and system design

**What changed:** Added the approved design documents for the final system architecture, database, recognition evaluation, and development roadmap.

**Previous behaviour:** The prototype did not have a documented application structure, relational data design, policy model, or reliable recognition evaluation method.

**New behaviour:** The project now has a design for a Flask and SQLAlchemy application, SQLite-to-PostgreSQL compatibility, configurable attendance policies, protected biometric lifecycle, database-level duplicate prevention, and a benchmark plan for comparing the preserved LBPH prototype with a possible embedding approach.

**Why this was changed:** These documents establish a safe, understandable foundation before any major code changes or GitHub publication.

**How it works:** The attendance engine is separated from face recognition. Recognition produces an evidence-based decision; the attendance service applies shift and policy rules in a database transaction. The final recognition choice is deferred until separate, consented data and a supported runtime permit a valid benchmark.

**Files created:**

- `PROJECT_ARCHITECTURE.md`
- `DATABASE_SCHEMA.md`
- `RECOGNITION_EVALUATION.md`
- `DEVELOPMENT_ROADMAP.md`

**Files modified:**

- `CHANGELOG.md`

**Files removed:** None. Existing LBPH source files, model artifact, and dataset were preserved.

**Bugs fixed:** No runtime bug fixes were made in this planning-only phase. The documentation identifies the `attendance.csv` directory/file conflict and policy/database safeguards needed for the later fix.

**Testing:** Documentation was reviewed against the Phase 1 audit. No runtime benchmark or application test was possible because the machine still has no usable Python runtime configured.

**Current status:** Design complete; awaiting Phase 2 review and approval. GitHub integration and Phase 3 are intentionally not started.

### 2026-11-02 — Phase 1 project audit

**What changed:** Added a written audit of the existing face-recognition prototype.

**Previous behaviour:** The project had no central record explaining what was implemented, what was missing, or what risks needed attention.

**New behaviour:** `PROJECT_AUDIT.md` now documents the structure, prototype recognition flow, gaps, technical risks, recommended architecture, database proposal, and phased roadmap.

**Why this was necessary:** The requested project process requires understanding the current work before any major changes are made.

**Files created:**

- `PROJECT_AUDIT.md`
- `CHANGELOG.md`

**Files modified or removed:** None. Existing source code, data, model artifacts, and directories were preserved.

**Testing:** Static inspection was completed. Runtime tests were not performed because this computer does not currently have a usable Python interpreter configured, and Phase 1 did not permit a pipeline rewrite.

**Current status:** Audit complete; awaiting approval for the Phase 2 architecture and database work.
