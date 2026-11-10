"""Validate uploaded still images before private storage.

Checks run from cheapest to most expensive:
  1. size limits      -> empty, too many bytes, too many pixels
  2. real image?      -> Pillow must decode it as JPEG or PNG
  3. face detection   -> exactly one face, large enough
  4. face quality     -> brightness, contrast and sharpness of the face region
Accepted images are re-encoded as JPEG, which drops hidden metadata (EXIF,
GPS location, camera details) so only pixels are stored.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from io import BytesIO
from typing import Mapping

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.utils.face_detector import HaarFaceDetector

# Quality is measured on the face resized to this square, so a face filmed
# close up and one filmed further away are scored on the same scale.
QUALITY_FACE_SIZE = 160


class ImageValidationError(ValueError):
    """A user-safe reason why an image was rejected."""


@dataclass(frozen=True)
class FaceQuality:
    brightness: float
    contrast: float
    sharpness: float
    face_width: int


@dataclass(frozen=True)
class ValidatedImage:
    data: bytes
    image_format: str
    width: int
    height: int
    quality: FaceQuality


class ImageValidator:
    permitted_formats = {"JPEG", "PNG"}

    def __init__(self, config: Mapping[str, object], detector=None) -> None:
        self.maximum_bytes = int(config["MAX_CONTENT_LENGTH"])
        self.maximum_pixels = int(config["ENROLLMENT_MAX_IMAGE_PIXELS"])
        self.minimum_face_width = int(config["ENROLLMENT_MIN_FACE_WIDTH"])
        self.minimum_sharpness = float(config["ENROLLMENT_MIN_SHARPNESS"])
        self.minimum_brightness = float(config["ENROLLMENT_MIN_BRIGHTNESS"])
        self.maximum_brightness = float(config["ENROLLMENT_MAX_BRIGHTNESS"])
        self.minimum_contrast = float(config["ENROLLMENT_MIN_CONTRAST"])
        self.detector = detector or HaarFaceDetector()

    def validate(self, data: bytes) -> ValidatedImage:
        image = self._decode(data)
        faces = list(self.detector.detect(image))
        if not faces:
            raise ImageValidationError("No face was detected. Face the camera in good light.")
        if len(faces) > 1:
            raise ImageValidationError("More than one face is visible. Only the employee should be in the frame.")

        x, y, face_width, face_height = (int(value) for value in faces[0])
        if face_width < self.minimum_face_width:
            raise ImageValidationError("The face is too small. Move closer to the camera.")

        quality = self._measure_face(image, x, y, face_width, face_height)
        if quality.brightness < self.minimum_brightness:
            raise ImageValidationError("The face is too dark. Add light in front of the employee.")
        if quality.brightness > self.maximum_brightness:
            raise ImageValidationError("The face is overexposed. Reduce direct or bright light.")
        if quality.contrast < self.minimum_contrast:
            raise ImageValidationError("The face has too little contrast. Improve the lighting and retake it.")
        if quality.sharpness < self.minimum_sharpness:
            raise ImageValidationError("The image is too blurry. Hold still and retake it.")

        height, width = image.shape[:2]
        return ValidatedImage(self._reencode(image), "jpg", width, height, quality)

    def _decode(self, data: bytes) -> np.ndarray:
        if not data:
            raise ImageValidationError("The uploaded image is empty.")
        if len(data) > self.maximum_bytes:
            raise ImageValidationError("The image is larger than the upload limit.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(data)) as source:
                    if source.format not in self.permitted_formats:
                        raise ImageValidationError("Only JPEG and PNG images are accepted.")
                    if source.width * source.height > self.maximum_pixels:
                        raise ImageValidationError("The image resolution is too large.")
                    source.verify()  # detects truncated or corrupt files
                with Image.open(BytesIO(data)) as source:
                    upright = ImageOps.exif_transpose(source)  # respect phone/camera rotation
                    rgb = upright.convert("RGB")
        except ImageValidationError:
            raise
        except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
            raise ImageValidationError("The uploaded file is not a valid image.") from error
        except (OSError, SyntaxError, ValueError) as error:
            raise ImageValidationError("The uploaded image is corrupt or unreadable.") from error

        if min(rgb.size) < self.minimum_face_width:
            raise ImageValidationError("The image is too small for reliable face checks.")
        return cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR)

    @staticmethod
    def _measure_face(image: np.ndarray, x: int, y: int, w: int, h: int) -> FaceQuality:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        crop = gray[max(y, 0) : y + h, max(x, 0) : x + w]
        if crop.size == 0:
            raise ImageValidationError("The detected face could not be measured. Retake the image.")
        face = cv2.resize(crop, (QUALITY_FACE_SIZE, QUALITY_FACE_SIZE), interpolation=cv2.INTER_AREA)
        return FaceQuality(
            brightness=round(float(face.mean()), 1),
            contrast=round(float(face.std()), 1),
            sharpness=round(float(cv2.Laplacian(face, cv2.CV_64F).var()), 1),
            face_width=w,
        )

    @staticmethod
    def _reencode(image: np.ndarray) -> bytes:
        success, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 92])
        if not success:
            raise ImageValidationError("The image could not be processed. Retake it.")
        return encoded.tobytes()
