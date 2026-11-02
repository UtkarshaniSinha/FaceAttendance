# Dataset Quality Report

**Audit date:** 2 November 2026
**Scope:** Read-only inspection of `dataset/`. No images, labels, models, or scripts were changed. No recognition model was trained or benchmarked.

## Conclusion

The current dataset is **not suitable** for developing, validating, or making reliability claims about an employee attendance recognition system. It is a small, low-resolution subset of celebrity face images, not a consented employee dataset. It may remain as a legacy LBPH demonstration input, but it must not be used for employee enrolment, production evaluation, or threshold selection.

Image enhancement cannot restore identity information that was never captured at this resolution, and it would not make this dataset a valid employee-attendance benchmark.

## Confirmed findings

### Structure and labels

| Item | Result |
| --- | --- |
| Image files | 140 JPEG files; no PNG/JPEG variants found |
| Label folders | 7 |
| Images per folder | 20 for each label |
| Labels | `Alejandro_Toledo`, `Alvaro_Uribe`, `Amelie_Mauresmo`, `Andre_Agassi`, `Angelina_Jolie`, `Ariel_Sharon`, `Arnold_Schwarzenegger` |
| Subject type | Celebrity/public-figure identities; no employee identity or consent metadata is present |
| Image dimensions | Every image is 47 Ã— 62 pixels (2,914 pixels) |
| Exact byte-for-byte duplicates | None (SHA-256 comparison) |
| Useful camera metadata | None found. The sole common JPEG property (`0x5090`) is not usable camera/EXIF capture information. |

The names and the project's `download_dataset.py` indicate that the images came from the scikit-learn Labeled Faces in the Wild (LFW) download flow. The origin is supported by the source code and labels; individual original capture conditions cannot be reconstructed from the local files.

### Measured file-level quality statistics

Measurements used an 8-bit grayscale conversion of each complete image. Brightness is mean grayscale intensity (0â€“255); dark/bright clipping counts pixels below 30 or above 225. Sharpness is variance of a Laplacian response: a comparative proxy within this same small, preprocessed setâ€”not a universal pass/fail score or a measure of face-recognition accuracy.

| Metric | Result |
| --- | --- |
| Mean brightness, all images | 120.14 / 255 |
| Brightness range | 73.66â€“163.17 / 255 |
| Mean contrast (grayscale standard deviation) | 42.21 |
| Mean dark-pixel share | 3.26% |
| Mean bright-pixel share | 1.09% |
| Images with more than 10% very dark pixels | 11 / 140 (7.9%) |
| Images with more than 10% very bright pixels | 3 / 140 (2.1%) |
| Median sharpness proxy | 533.23 |
| Sharpness proxy range | 139.72â€“1,340.61 |
| Images below proxy value 300 | 12 / 140 (8.6%) |

The brightness range, clipped-pixel counts, and sharpness spread confirm uneven exposure/contrast and a measurable low-detail subset. All images are extremely low resolution by modern recognition-evaluation standards. Visual inspection of representative low-light and low-sharpness files also confirms that the set is tightly cropped, grayscale face imagery with limited fine facial detail.

### Per-label balance

The label count is balanced (20 files per identity), but balanced file counts do **not** prove independent captures. There is no session, camera, date, pose, lighting, distance, or consent metadata. A simple exact-hash check cannot identify near-duplicates, adjacent video frames, or photos from the same capture session.

## Quality problems and risks

1. **Very low resolution:** 47Ã—62 is insufficient to represent the detail expected from a webcam attendance kiosk and makes image quality/pose judgement limited.
2. **Variable illumination and exposure:** 11 files have more than 10% very dark pixels and three have more than 10% very bright pixels; overall brightness varies widely.
3. **Uneven sharpness/detail:** 12 images fall into the low end of this dataset's Laplacian sharpness distribution. This is a warning signal, not proof that every such image is unusable.
4. **No capture metadata:** Independent sessions and realistic operating conditions cannot be verified.
5. **Wrong subject population:** Celebrity images provide no evidence about recognition of intended employees, consent, or deployment camera conditions.
6. **Insufficient independent data:** 20 images per identity is small, and the absence of session metadata means a train/validation/test split cannot be confidently made independent. The current scripts test images from the training collection, which is invalid for performance estimates.
7. **No unknown-person protocol:** A meaningful false-acceptance test needs identities who were never enrolled; this set does not define such an evaluation protocol.

## Facial visibility: what is and is not known

**Confirmed:** The files are small, cropped, grayscale face thumbnails. Representative visual checks show a visible face in the inspected samples, but limited detail and uneven illumination.

**Not confirmed:** This audit did not run a face detector, landmark model, occlusion classifier, pose estimator, or human review of all 140 images. It therefore cannot provide a reliable count of fully visible faces, exact yaw/pitch angles, occlusions, or detector success rate. Those require a supported runtime and a dedicated validation process.

## Suitability assessment

| Intended use | Assessment | Reason |
| --- | --- | --- |
| Preserve original prototype | Acceptable | Keeps the history of the learning experiment intact. |
| Demonstrate an LBPH code path internally | Limited | Only if clearly labelled as a celebrity-image prototype with no accuracy/security claim. |
| Train employee templates | Not suitable | Subjects are not employees and consent/retention information is absent. |
| Evaluate FAR/FRR/accuracy for attendance | Not suitable | No independent sessions, unknown-subject protocol, realistic conditions, or sufficient data. |
| Calibrate a deployment threshold | Not suitable | The data/camera conditions do not represent the deployment. |
| Public GitHub sample data | Not recommended by default | Identifiable face data is sensitive and unnecessary; exclude it through `.gitignore` during GitHub preparation. |

## New dataset collection and validation recommendations

Collect data only after consent, with a written purpose/retention notice and a deletion contact/process. Do not collect real employee biometrics for a classroom demonstration unless authorised; synthetic or consented volunteers are safer for development.

### Minimum capture requirements

- Use the same or a representative webcam planned for the kiosk; capture colour frames at **at least 640Ã—480**, retaining a face crop of roughly **160Ã—160 pixels or greater** after detection.
- Capture several *independent sessions* per participant, preferably on different days or after meaningful changes of lighting/clothing/camera position.
- For each session, capture frontal plus modest left/right/up/down pose variation, normal/low/bright lighting, and intended near/normal/far distances.
- Keep the face unobstructed for core enrolment samples; record glasses, masks, and significant occlusions as separately labelled test conditions rather than silently mixing them in.
- Reject images with multiple faces, extreme blur, severe under/over-exposure, closed/partly visible face, or a face that is too small.
- Assign opaque participant IDs, not names, in the research/evaluation dataset. Keep consent records separate and access-controlled.
- Do not store raw capture images longer than necessary. Record why an image was retained/rejected and delete temporary files on the agreed schedule.

### Suggested evaluation composition

- Enrol sufficient identities to reflect the intended demonstration scope, with **at least three independent sessions per enrolled identity**.
- Split by session, not random image: enrolment images in one set, threshold validation in another, and final testing in a third.
- Include a separate, non-enrolled group for unknown-face/FAR testing.
- Pre-register quality gates and success criteria before selecting a recognizer or threshold.
- Record device, resolution, lighting category, approximate distance, pose category, and capture sessionâ€”without unnecessary personal metadata.

## Required stage before model evaluation

Dataset collection and validation is now a dedicated prerequisite in `DEVELOPMENT_ROADMAP.md`. No LBPH retraining or embedding-model benchmark may occur until a consented dataset passes the agreed quality checks and has an independent evaluation split.

`PUBLIC_DATASET_RESEARCH.md` documents public benchmark options and their licence gates. Public celebrity data can support a controlled research question only; it does not change this report's conclusion or replace consented attendance-camera validation.

## Assumptions and limitations

- The source is inferred from `download_dataset.py` and the LFW-style names, not from provenance metadata embedded in each image.
- The quality measurements apply to entire images, not precisely detected face regions.
- Exact hashes only rule out identical files; they do not rule out visually similar or correlated images.
- Numerical quality proxies guide review; they cannot alone predict recognition performance, identity correctness, bias, or liveness resistance.
