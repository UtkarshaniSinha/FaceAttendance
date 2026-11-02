# Testing Guide

## Verified result

On 3 November 2026, the Phase 1 test suite was run with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Result: **12 passed**. The application factory was also instantiated successfully and the source/tests were compiled with `compileall`.

## Current coverage

| Layer | Verified coverage | Status |
| --- | --- | --- |
| Application | Factory startup, SQLite setup, dashboard response and summary counts. | Implemented and tested |
| Employee | Required fields, unique code, create/list/edit/deactivate flows. | Implemented and tested |
| Attendance | Employee relationship, one-record-per-day rule, inactive employee rejection, database foreign-key rejection. | Implemented and tested |
| Recognition | None. | Not started; requires separately approved data and model licences |
| Camera/hardware | None. | Not implemented |
| Security | No authentication, CSRF, or authorisation tests yet. | Not implemented |

## Test-data rules

- Use synthetic fixtures for ordinary automated tests.
- Keep consented biometric evaluation data outside the repository.
- Separate enrolment, validation, and final test sessions; include people not enrolled in the gallery.
- Do not quote recognition results unless the command, dataset scope, hardware, model version, threshold protocol, and observed output are recorded.
