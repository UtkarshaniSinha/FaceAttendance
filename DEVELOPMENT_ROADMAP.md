# Development Roadmap

**Current position:** Phase 2 design complete; waiting for review. Each phase will be tested before being called complete.

| Phase | Goal | Evidence of completion | Status |
| --- | --- | --- | --- |
| 1 | Audit the existing prototype | `PROJECT_AUDIT.md` and changelog entry | Complete |
| 2 | Design architecture, schema, evaluation, privacy, deployment, and test plan | Phase 2 documents in the repository root | Complete; awaiting approval |
| GitHub milestone | Create/prepare repository, review files, then commit/push only with explicit publication approval | Remote URL and approved Phase 2 commit | Blocked until Phase 2 approval |
| 3 | Set up supported Python, dependency lock/specification, configuration, Git hygiene | Reproducible local setup and environment checks | Not started |
| 4 | Implement data foundation and secure administrator login | Migrations, model tests, authentication tests | Not started |
| 5 | Implement employees, departments, shifts, policies, consent, and biometric lifecycle | CRUD/integration tests; manual consent flow check | Not started |
| 6 | Review/approve dataset and model licences; collect and validate a consented evaluation dataset | Licence decision log, capture-quality log, consent/retention confirmation, independent session split, unknown-subject set, and quality-gate sign-off | Not started; mandatory before model evaluation |
| 7 | Evaluate a pretrained ArcFace-style model and preserved LBPH baseline using validated data plus approved public verification benchmarks | Completed `RECOGNITION_EVALUATION.md` results and recommendation | Not started |
| 8 | Implement recognition adapter and attendance engine | Tests for check-in/out, cooldown, duplicate prevention, late/early calculation, camera failures | Not started |
| 9 | Build dashboard, kiosk feedback, history, and reports | UI/manual accessibility checks and export tests | Not started |
| 10 | Hardening and release preparation | Security/privacy review, deployment guide, test report, final GitHub review | Not started |

## Testing strategy

Tests will be grouped by purpose:

- **Unit tests:** validation, policy decisions, late/early calculations, date/time handling, and report calculations.
- **Database tests:** constraints, migrations, duplicate attendance prevention, transactions, and deletion/revocation lifecycle.
- **Integration tests:** login/access control, employee flow, attendance flow, filters, and exports.
- **Recognition benchmarks:** separate enrolment/validation/test data; known and unknown identities; controlled condition matrix; FAR/FRR/speed recorded.
- **Manual hardware tests:** camera unavailable/disconnected, multiple faces, dim/bright scenes, distance, angle, restart persistence, and clear operator feedback.
- **Security checks:** unauthenticated access rejection, role limits, CSRF/input validation, no secrets/raw biometric data in Git, and deletion audit trail.

No test will be described as passed until its command, test data scope, and result are recorded in `TESTING.md` during implementation.

## Career learning map

| Phase | What you will build | Technologies and interview concepts |
| --- | --- | --- |
| 3–4 | Flask foundation, configuration, database, login | Python OOP, Flask/REST APIs, SQLAlchemy, migrations, password hashing, pytest. |
| 5 | Employees, shifts, consent, and policies | Relational design, validation, audit trails, privacy-by-design. |
| 6 | Lawful data/model selection and evaluation data | Dataset/model licensing, independent splits, consent, image-quality gates. |
| 7 | Embedding comparison laboratory | Detection vs recognition, ArcFace embeddings, cosine similarity, thresholds, FAR/FRR, latency. |
| 8–9 | Attendance workflow, dashboard, and reports | Transactions, HTML/CSS/JavaScript, charts, exports, integration tests. |
| 10 | Release preparation | Docker, deployment configuration, security checks, documentation, Git/GitHub. |

## Future GitHub preparation (after Phase 2 approval)

The next approved milestone will inspect Git state again, create the requested README/setup/testing/dependency files and `.gitignore`, show the exact publication set, and ask before any commit or push. No GitHub account, remote, commit, or push has been created in Phase 2.

### Proposed GitHub publication list

Planned to publish after review: Python source code (including preserved legacy scripts), documentation (`README.md`, audit, architecture, schema, dataset/model research, roadmap, installation and testing guides), dependency specification, `.env.example` without secrets, Docker files if later created, and automated tests using synthetic/non-biometric fixtures.

Planned to exclude: `dataset/`, any future consented capture data, `trainer.yml`, `labels.pickle`, downloaded pretrained model weights, biometric templates, local databases, attendance exports, `.env` files, virtual environments, caches, and IDE settings. The final `.gitignore` and publication list will be shown for explicit approval before any commit or push.
