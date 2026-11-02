# Recognition Evaluation Plan

**Phase:** 2 planning and environment assessment.
**Status:** No recognition benchmark has been run. There is no installed/default Python runtime on this computer, and the current dataset is unsuitable for an employee-system claim.

## Dataset quality gate

The read-only audit in `DATASET_QUALITY_REPORT.md` found 140 low-resolution (47Ã—62) celebrity thumbnails, with no employee consent/capture metadata and no defensible independent train/validation/test split. This dataset is prohibited from future employee-model training, FAR/FRR measurement, threshold calibration, or deployment claims. Dataset collection and validation must be completed before any model evaluation.

## Existing LBPH baseline

The project currently uses OpenCV Haar Cascade detection and OpenCV LBPH recognition. Its advantages are small size, offline operation, and a simple training path. Its disadvantages are high sensitivity to lighting, pose, cropping, and camera variation. It also offers no meaningful biometric security or liveness protection by itself.

The present model and diagnostic scripts cannot provide a valid baseline because they use the same 140 LFW celebrity images for training and testing. Such a test can memorise images and does not measure performance on new images, unknown people, a webcam, different lighting, angle, or distance.

## Candidate approaches

| Option | Benefits | Limitations | Decision now |
| --- | --- | --- | --- |
| Preserve LBPH | Works with existing artifacts; light and offline; easy to explain | Weak generalisation and spoof resistance; training/preprocessing consistency problem | Keep as a legacy comparison baseline only. |
| Embedding recognizer with OpenCV DNN detector | Better separation across lighting/pose; supports threshold calibration; OpenCV remains central | Requires verified model files and careful calibration; more setup than LBPH | Preferred candidate for controlled kiosk evaluation. |
| DeepFace/other high-level framework | Convenient access to multiple modern models | Larger dependency footprint, variable model/download licensing, harder reproducibility | Do not add unless the OpenCV-DNN route cannot meet measured needs. |
| Cloud recognition API | May be accurate and managed | Privacy, recurring cost, network dependency, biometric data transfer | Not recommended for this local-first project. |

## Recommended pipeline, pending evidence

Use a modern face detector through an OpenCV-compatible adapter, perform quality and exactly-one-face checks, create/retrieve an embedding from an approved local model, then compare it against registered employee templates with a calibrated distance threshold and multi-frame confirmation. Keep LBPH code intact as the legacy baseline.

This is a design recommendation, **not** a claim of measured superiority in this project. A final choice requires the benchmark below.

## Preferred research model

Subject to model-term approval, start with a pretrained ArcFace-style InsightFace embedding model rather than train from scratch or fine-tune. OpenCV will remain responsible for frames and quality checks; the recognizer will align a single face, generate a normalized embedding, and compare it to consented employee templates with cosine similarity.

InsightFace code is MIT, but its public pretrained model packs are non-commercial research only. Model weights must not be committed to Git or used commercially without separate authorisation. `PUBLIC_DATASET_RESEARCH.md` records dataset and model access/licensing gates.

## Evaluation methodology

### Data and consent

- Do not use the current celebrity dataset for employee claims or production registration.
- Do not train or benchmark either candidate on it for this project; preserve it only as a legacy prototype artifact.
- Public verification benchmarks measure 1:1 pairs; they do not replace consented employee/webcam evaluation of open-set attendance matching.
- Obtain explicit written consent for a small, separate demonstration dataset, or use clearly licensed/synthetic evaluation data where appropriate.
- Complete the capture-quality and independent-session validation stage defined in `DATASET_QUALITY_REPORT.md` before splitting or evaluating data.
- Keep identities disjoint across training/enrolment and testing. For each enrolled person, reserve separate sessions/images for testing.
- Include unknown volunteers/data not present during enrolment to measure false acceptance.

### Conditions

For each participant, capture testing sessions at normal/low/bright lighting, near/normal/far camera distance, frontal/left/right/up/down angles, and at least two different sessions or days where possible. Record camera/device, condition, and whether the face is known or unknown.

### Metrics

| Metric | Meaning | Calculation |
| --- | --- | --- |
| Recognition accuracy | Correct accepted identity among evaluated known-face attempts | correct identities / all known attempts (report rejection separately) |
| False acceptance rate (FAR) | Unknown or wrong identity accepted as an enrolled person | false accepts / impostor attempts |
| False rejection rate (FRR) | Enrolled person rejected or mismatched | false rejects / genuine attempts |
| Processing speed | Suitability for a webcam kiosk | median and p95 milliseconds per frame/face, plus achieved FPS |
| Hardware use | Deployment practicality | CPU/GPU, memory, OS, camera resolution, model size |
| Installation complexity | Reproducibility | documented install steps, download/model requirements, and failure points |

Thresholds must be selected on a validation split, then reported once on a separate hold-out test split. Do not tune the threshold while looking at final test results.

### Decision rule

Choose the lowest-complexity method that meets pre-agreed safety and usability targets on hold-out data, prioritising low false acceptance for attendance integrity. Record uncertainty and failure conditions. If neither method meets targets, keep the system in demonstration-only status and do not use it for actual attendance decisions.

## Current results

| Method | FAR | FRR | Accuracy | Speed | Result |
| --- | --- | --- | --- | --- | --- |
| Current LBPH | Not measured | Not measured | Not measured | Not measured | Runtime unavailable; existing test methodology is invalid. |
| Embedding candidate | Not measured | Not measured | Not measured | Not measured | Not installed/evaluated. |

## Liveness and presentation attacks

The current prototype has no liveness check. Face detection, face movement, or blink detection can improve interaction feedback but cannot reliably distinguish a live person from a high-quality photo, video replay, or mask. Stronger presentation-attack detection needs a validated PAD model, appropriate capture hardware, attack testing, and clear operating limitations. It is outside Phase 2 implementation and must be evaluated separately before any security claim.

## Reuse/refactor decision

- Reuse: camera access concepts, OpenCV installation knowledge, and the legacy LBPH files as a documented baseline.
- Refactor later: duplicated training scripts, hard-coded paths/thresholds, direct CSV attendance writing, and detection/recognition logic mixed with UI loop.
- Replace only after approval and a reproducible benchmark: the production recognition adapter, not the preserved legacy scripts.
