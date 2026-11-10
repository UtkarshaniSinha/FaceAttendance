"""Face detection only: finds where faces are, never who they belong to."""

from __future__ import annotations

import cv2
import numpy as np


class HaarFaceDetector:
    """OpenCV's bundled frontal-face Haar cascade (no download required).

    Haar cascades are fast and offline but weaker with side poses and poor
    light. That is acceptable for guided enrolment, where the employee faces
    the camera, and the detector can be swapped later behind ``detect``.
    """

    def __init__(self, min_size: int = 60) -> None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._cascade = cv2.CascadeClassifier(cascade_path)
        if self._cascade.empty():
            raise RuntimeError("OpenCV Haar cascade could not be loaded.")
        self._min_size = (min_size, min_size)

    def detect(self, image: np.ndarray):
        """Return a list of (x, y, width, height) face boxes in a BGR image."""

        gray = cv2.equalizeHist(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
        faces = self._cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=6, minSize=self._min_size
        )
        return [tuple(int(v) for v in face) for face in faces]
