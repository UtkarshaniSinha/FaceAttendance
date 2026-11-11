"""Turn a face image into an embedding using OpenCV's YuNet + SFace models.

Pipeline for one image:

    BGR image ──YuNet──> face box + 5 landmarks (eyes, nose, mouth corners)
              ──alignCrop──> 112x112 face, rotated so the eyes are level
              ──SFace──> 128 numbers (the embedding), scaled to length 1

Both models run inside the installed opencv-contrib-python package
(cv2.FaceDetectorYN and cv2.FaceRecognizerSF), so no extra Python package is
needed. The .onnx model files are NOT in Git: they live in a private folder
(default: instance/models) and are checked for here.

Licences (OpenCV Zoo): YuNet - MIT; SFace - Apache-2.0. See docs/evaluation.md.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Mapping

import cv2
import numpy as np

from app.recognition.matcher import l2_normalize

MODEL_NAME = "opencv-sface-2021dec"  # stored with every template
EMBEDDING_SIZE = 128


class RecognitionUnavailable(RuntimeError):
    """The model files are missing or cannot be loaded (safe to show users)."""


class RecognitionImageError(ValueError):
    """The image cannot be used for recognition (safe to show users)."""


class SFaceEmbedder:
    model_name = MODEL_NAME

    def __init__(self, config: Mapping[str, object]) -> None:
        model_dir = Path(str(config["RECOGNITION_MODEL_DIR"]))
        detector_path = model_dir / str(config["FACE_DETECTOR_MODEL"])
        recognizer_path = model_dir / str(config["FACE_RECOGNIZER_MODEL"])
        missing = [p.name for p in (detector_path, recognizer_path) if not p.is_file()]
        if missing:
            raise RecognitionUnavailable(
                "Face recognition is not installed: missing model file(s) "
                + ", ".join(missing)
                + ". See the Setup section of README.md."
            )
        try:
            self._detector = cv2.FaceDetectorYN.create(
                str(detector_path), "", (320, 320),
                float(config["RECOGNITION_DETECTION_SCORE"]), 0.3, 5000,
            )
            self._recognizer = cv2.FaceRecognizerSF.create(str(recognizer_path), "")
        except cv2.error as error:
            raise RecognitionUnavailable("The face recognition model files could not be loaded.") from error
        # OpenCV model objects are not safe to share between threads at once.
        self._lock = threading.Lock()

    def detect(self, image: np.ndarray) -> np.ndarray:
        """Return YuNet rows: [x, y, w, h, 10 landmark values, score]."""

        height, width = image.shape[:2]
        with self._lock:
            self._detector.setInputSize((width, height))
            _, faces = self._detector.detect(image)
        return np.empty((0, 15), dtype=np.float32) if faces is None else faces

    def detect_boxes(self, image: np.ndarray) -> list[tuple[int, int, int, int]]:
        """Face boxes only, in the format ImageValidator expects."""

        return [tuple(int(v) for v in row[:4]) for row in self.detect(image)]

    def embed_face(self, image: np.ndarray, face_row: np.ndarray) -> np.ndarray:
        """Align one detected face and return its normalised embedding."""

        with self._lock:
            aligned = self._recognizer.alignCrop(image, face_row)
            feature = self._recognizer.feature(aligned)
        return l2_normalize(feature)

    def embed_single(self, image: np.ndarray) -> np.ndarray:
        """Embedding for an image that must contain exactly one face."""

        faces = self.detect(image)
        if len(faces) == 0:
            raise RecognitionImageError("No face was detected. Face the camera in good light.")
        if len(faces) > 1:
            raise RecognitionImageError("More than one face is visible. Only one person should be in the frame.")
        return self.embed_face(image, faces[0])


class EmbedderBoxDetector:
    """Lets ImageValidator count and size faces with the same detector (YuNet)."""

    def __init__(self, embedder) -> None:
        self._embedder = embedder

    def detect(self, image: np.ndarray):
        return self._embedder.detect_boxes(image)


def embedding_to_bytes(embedding: np.ndarray) -> bytes:
    vector = l2_normalize(embedding)
    if vector.size != EMBEDDING_SIZE:
        raise ValueError("Unexpected embedding size.")
    return vector.astype("<f4").tobytes()


def embedding_from_bytes(data: bytes) -> np.ndarray:
    vector = np.frombuffer(data, dtype="<f4")
    if vector.size != EMBEDDING_SIZE:
        raise ValueError("Stored embedding has an unexpected size.")
    return vector
