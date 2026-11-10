# Testing Guide

## How to run

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

`pytest.ini` limits collection to `tests/`, so the legacy scripts in the project root (`test_photo.py`, `test_dataset_faces.py`) are not run as tests.

## Latest automated result

10 November 2026 (Linux, Python 3.13, Flask 3.1, OpenCV 4.14): **52 passed**.
Earlier result: 3 November 2026, Phase 1, **12 passed** (Windows, Python 3.12).

## Coverage

| Area | What the tests check | File |
| --- | --- | --- |
| App and dashboard | Factory, SQLite tables, dashboard counts, local-time display | `test_app.py` |
| Employees | Required fields, unique ID, create/list/edit/deactivate | `test_employees.py` |
| Attendance | One record per employee per day, inactive employee, foreign keys | `test_attendance.py` |
| CSRF | Protection on in tests; token present in every POST form; registration succeeds with the token taken from the rendered form; missing, wrong and other-session tokens are rejected with 400 | `test_csrf.py` |
| Consent | Checkbox required, no capture without consent, inactive employees blocked | `test_enrollment.py` |
| Image validation | No face, two faces, small face, dark, overexposed, low contrast, blurry, empty, not an image, GIF, too small, truncated, over size limit, over pixel limit; PNG accepted; stored JPEG has no EXIF | `test_enrollment.py` |
| Storage and lifecycle | Full consent → capture → complete workflow; random names outside `static/`; no paths in replies; remove one image; cross-employee removal blocked; min/max image counts; delete images; withdraw consent keeps attendance; database failure removes the stored file; path traversal blocked | `test_enrollment.py` |

**Test images are synthetic.** No real faces are used (the celebrity dataset is rejected and no new data is approved). Most validation tests use a stub detector that reports chosen face boxes; the real OpenCV detector is tested only on images without faces (it must reject them).

## Browser check (headless Chrome, fake camera) — 10 November 2026

Run against the real app with Chrome's built-in fake camera, which shows a moving pattern, not a face:

- Registration through the real form with CSRF: works.
- Consent → start enrolment → camera starts → capture → preview → upload: the server correctly rejected the frame with "No face was detected"; Retake returned to the live view.
- With a stub detector that "finds" one face (scratch launcher only, not part of the app): 3 photos accepted, one removed, one retaken, enrolment completed, consent withdrawn, files deleted, list and dashboard updated. No JavaScript errors.

## Still needs a manual check with a real webcam

- A real face is accepted, and a second person in frame is rejected.
- Quality thresholds feel right in your room lighting (adjust `ENROLLMENT_MIN_*` in `.env` if good photos are rejected).
- Camera permission prompts and the "camera busy" message in Chrome/Edge on Windows.

## Test-data rules

- Use synthetic fixtures for ordinary automated tests.
- Keep consented biometric evaluation data outside the repository.
- Separate enrolment, validation, and final test sessions; include people not enrolled in the gallery.
- Do not quote recognition results unless the command, dataset scope, hardware, model version, threshold protocol, and observed output are recorded.
