# Testing Guide

## Current test status

No automated application tests have run. There is no implemented Flask application and this workspace has no usable Python runtime. The existing `test_photo.py` and `test_dataset_faces.py` are legacy diagnostic scripts, not automated tests: they use the same legacy dataset collection as training and cannot establish recognition reliability.

## Planned test layers

| Layer | Planned coverage | Current status |
| --- | --- | --- |
| Unit | Employee validation, shift/policy calculations, late/early rules, and report calculations. | Not implemented |
| Database | Constraints, migrations, duplicate attendance prevention, transactions, and retention/deletion lifecycle. | Not implemented |
| Integration | Login, role access, employee flow, enrolment consent, attendance state transitions, and exports. | Not implemented |
| Recognition | Separate known/unknown sessions, quality gates, threshold selection, FAR, FRR, accuracy, and latency. | Not started; requires approved data/model licences |
| Hardware | Camera disconnect, multiple faces, lighting, pose/distance, restarts, and feedback. | Not started |
| Security | Authentication, CSRF, validation, secret scanning, access boundaries, and audit logs. | Not implemented |

## Test-data rules

- Use synthetic fixtures for ordinary automated tests.
- Keep consented biometric evaluation data outside the repository.
- Separate enrolment, validation, and final test sessions; include people not enrolled in the gallery.
- Do not quote recognition results unless the command, dataset scope, hardware, model version, threshold protocol, and observed output are recorded.

## Planned command

After a Python runtime and tests exist, the expected command is `pytest`. It is not currently runnable or verified in this repository.
