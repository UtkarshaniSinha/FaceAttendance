# Testing and evaluation

## What the automated tests check

199 pytest tests, run with `pytest -q` or VS Code's Testing panel.

| Area | Examples |
| --- | --- |
| Matching logic | cosine similarity, threshold, unknown faces rejected, near-ties rejected |
| Check-in | only a confident match records attendance; inactive / no consent / withdrawn consent / unfinished enrolment never do; one record per day, even with 8 requests at the same time |
| Enrolment | consent required; photos with no face, two faces, too dark, blurry, not an image or too large are rejected |
| Privacy | photos stored outside `static/`, random names, deleting photos also deletes embeddings, attendance is kept |
| Security | CSRF on every form, login, lockout after 5 wrong passwords, kiosk can only check in, error pages show no internal details |
| Models | YuNet and SFace load and give the same 128 numbers for the same image (skipped if the model files are missing) |

The matching tests use made-up embeddings, so I can control who "looks like" whom. **That proves the logic is right, not that real faces are recognised well.**

## What has and hasn't been measured

| Question | Status |
| --- | --- |
| Is a real enrolled person recognised through the webcam? | Yes for one person (me), in a small first test on 11 Nov 2026 (see below) |
| How often is the right person rejected (FRR)? | Not measured |
| How often is a stranger accepted (FAR)? | Not measured (needs other people's faces) |
| Are 0.45 and 0.05 good values? | Not tuned, starting values only |
| Can it be fooled with a photo? | Yes, there is no liveness check |

## Why these models

- **YuNet** (face detector, MIT licence) and **SFace** (face recogniser, Apache-2.0 licence), both from the OpenCV Model Zoo. They run inside OpenCV, so no extra packages were needed.
- The SFace model card doesn't name its training data, and the SFace paper used research face datasets, so I treat it as fine for a student project but not for commercial use.
- I don't use any face dataset. Recognition only uses photos taken through the app's consent screen.

## Threshold choice

OpenCV suggests 0.363 for comparing two photos of one person. My app compares a photo against everyone enrolled, which gives more chances for a wrong match, so I started stricter at 0.45. The 0.05 gap means: if two employees score almost the same, the app refuses to guess.

## My own webcam test

| Date | Setup | Check-in attempts | Matched | Wrongly rejected | Similarity | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 11 Nov 2026 | Webcam (light and distance not recorded) | 2 | 2 | 0 | about 0.8 (read from the screen) | All enrolment photos were accepted. 1st check-in: "Attendance recorded". 2nd: "Already checked in today", so no duplicate record |

Next time: more attempts on different days, in dim light and at different distances, and write down the lowest similarity seen.

This only shows results for one person (me). It doesn't show how often a stranger would be accepted.
