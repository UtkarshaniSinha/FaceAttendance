# FaceAttendance

A Flask web app that marks employee attendance using face recognition. An employee gives consent, registers their face with the webcam, and after that they can check in just by looking at the camera.

This is a college portfolio project that runs on one computer. It is not a finished commercial product (see [Limitations](#limitations)).

## Why I built this

_(Write this part yourself before publishing: what got you interested, what you wanted to learn, and what your first version looked like.)_

## Features

- Register, edit, deactivate and reactivate employees
- Consent screen before any face photo is taken; consent can be withdrawn, which deletes the photos and face data
- Face enrolment with the browser webcam: take 3 to 10 photos, retake any of them; the server rejects photos with no face, two faces, or bad lighting/blur
- Face check-in: recognises an enrolled employee and marks attendance once per day
- Unknown faces and "too close to call" matches are rejected and nothing is recorded
- Admin login, plus a "kiosk" account that can only open the check-in page
- Dashboard with today's attendance and recent check-ins

## How recognition works

```
webcam photo
   │
   ▼
YuNet ──── finds the face and 5 landmarks (eyes, nose, mouth corners)
   │
   ▼
SFace ──── turns the aligned face into 128 numbers (an "embedding")
   │
   ▼
compare with every enrolled employee using cosine similarity
   │
   ├── best score below 0.45 ............ UNKNOWN    → nothing recorded
   ├── top two people within 0.05 ....... AMBIGUOUS  → nothing recorded
   └── otherwise ........................ MATCH
                                            │
                                            ▼
                    is the employee active, consented and enrolled?
                                            │
                                            ▼
                    record attendance (only once per day)
```

Two photos of the same person give embeddings that point in a similar direction, so their cosine similarity is high. The threshold (0.45) and the gap (0.05) are starting values I picked, not tuned on real data yet.

Duplicate attendance is blocked twice: the code checks for an existing record, and the database has a unique rule on (employee, date), so even two requests at the same moment can't both save.

## Why I switched from LBPH to SFace

My first version used OpenCV's LBPH recogniser, trained on a small public set of celebrity photos (low resolution, and I tested on the same photos I trained on, so the results meant nothing). I dropped that dataset and replaced LBPH with SFace, a pretrained embedding model from the OpenCV Model Zoo. SFace doesn't need retraining when a new employee is added, and it gives a similarity score I can set a threshold on. The old prototype is still in the Git history (first commit).

## Tech stack

Python 3.12, Flask, Flask-SQLAlchemy, SQLite, OpenCV (YuNet + SFace through `opencv-contrib-python`), NumPy, HTML/CSS/JavaScript, pytest.

## Project structure

```
app/
  routes/        pages and form handling (employees, enrolment, check-in, login)
  services/      the rules (attendance, enrolment, check-in, users)
  recognition/   YuNet + SFace + the matching logic
  models/        database tables
  utils/         image checks and private photo storage
  templates/, static/
tests/           pytest tests
run.py           starts the app
```

## Setup (Windows)

1. Create the virtual environment and install packages:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Download the two model files from the OpenCV Model Zoo and put them in `instance\models\` (they are not in Git):

   | File | Link | SHA-256 |
   | --- | --- | --- |
   | `face_detection_yunet_2023mar.onnx` | [download](https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx) | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |
   | `face_recognition_sface_2021dec.onnx` | [download](https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx) | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` |

   Check a download with `Get-FileHash instance\models\<file> -Algorithm SHA256`.

3. Run it: in VS Code open `run.py` and choose **Run Python File** (or run `python run.py`), then open `http://127.0.0.1:5000` in Chrome or Edge. The first page asks you to create the admin account.

No `.env` file is needed. The database, a random secret key and the face photos are created in the `instance\` folder, which is never committed.

## Tests

Run them from VS Code's Testing panel, or with `pytest -q`. There are 199 tests (sign-in, CSRF, consent, photo checks, matching rules, duplicate check-ins, deletion and more). The matching tests use made-up embeddings, so they check the logic, not how well real faces are recognised. See [docs/evaluation.md](docs/evaluation.md) for what has and hasn't been tested.

## Security

| Protection | What it prevents |
| --- | --- |
| Login on every page, admin and kiosk roles | Strangers using the app; the check-in screen can't open employee data |
| Passwords stored as salted scrypt hashes | Readable passwords if the database is stolen |
| Account locked for 15 minutes after 5 wrong passwords | Password guessing |
| Sessions end after 30 idle minutes | Someone using a computer left signed in |
| CSRF token on every form and JavaScript request | Another website submitting forms in your name |
| SQLAlchemy queries and Jinja auto-escaping | SQL injection and injected scripts (XSS) |
| Security headers (Content-Security-Policy, X-Frame-Options and others) | Clickjacking, scripts from other sites, file-type guessing |
| Upload checks (real JPEG/PNG, size limit, exactly one face) | Fake or oversized files |
| Random secret key, debug mode off, error pages without details | Forged cookies and leaking internal information |

Not included (future work): two-factor login, HTTPS and an audit log.

## Privacy

- No face photo is taken before the employee agrees to a consent notice.
- Photos are saved with random names in a private folder (not in `static/`), and embeddings are saved in the local database. Neither is shown on any page or written to logs.
- Withdrawing consent deletes the photos and embeddings. Attendance history is kept.
- Photos, embeddings, the database and the model files are excluded from Git.

## Limitations

- **No liveness check:** a printed photo or a phone screen showing an enrolled person could fool it.
- **Accuracy not measured:** I have not measured accuracy, false accept or false reject rates on real faces. The thresholds are not tuned yet.
- Runs on one computer only (SQLite, Flask's development server, no HTTPS).
- Password-only login, no audit log.

## Challenges and what I learned

_(Write this yourself: for example the CSRF "Invalid token" bug on the register form, why LBPH didn't work, the Windows file-lock bug when deleting photos, and how you prevented duplicate attendance.)_

## Future improvements

- Measure accuracy properly and tune the threshold
- Liveness detection
- Export attendance as CSV
