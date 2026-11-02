
import os

import cv2
import numpy as np
from PIL import Image


# -----------------------------
# CONFIGURATION
# -----------------------------

DATASET_DIR = "dataset"
MODEL_FILE = "trainer.yml"
LABELS_FILE = "labels.pickle"

IMAGE_SIZE = (200, 200)
CONFIDENCE_THRESHOLD = 100


# -----------------------------
# CHECK REQUIRED FILES
# -----------------------------

if not os.path.isdir(DATASET_DIR):
    raise FileNotFoundError(
        f"Dataset directory not found: {DATASET_DIR}"
    )

if not os.path.isfile(MODEL_FILE):
    raise FileNotFoundError(
        f"Trained model not found: {MODEL_FILE}"
    )

if not os.path.isfile(LABELS_FILE):
    raise FileNotFoundError(
        f"Label file not found: {LABELS_FILE}"
    )


# -----------------------------
# LOAD MODEL AND LABELS
# -----------------------------

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read(MODEL_FILE)

import pickle

with open(LABELS_FILE, "rb") as file:
    label_ids = pickle.load(file)

labels = {value: name for name, value in label_ids.items()}


# -----------------------------
# LOAD FACE DETECTOR
# -----------------------------

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades
    + "haarcascade_frontalface_default.xml"
)

if face_cascade.empty():
    raise RuntimeError("Could not load the Haar Cascade detector.")


# -----------------------------
# PROCESS DATASET IMAGES
# -----------------------------

for person_name in sorted(os.listdir(DATASET_DIR)):

    person_folder = os.path.join(DATASET_DIR, person_name)

    if not os.path.isdir(person_folder):
        continue

    print(f"\nProcessing images for: {person_name}")

    for image_file in sorted(os.listdir(person_folder)):

        if not image_file.lower().endswith(
            (".jpg", ".jpeg", ".png")
        ):
            continue

        image_path = os.path.join(person_folder, image_file)

        try:
            image = Image.open(image_path).convert("L")
            image_array = np.array(image, dtype=np.uint8)

            faces = face_cascade.detectMultiScale(
                image_array,
                scaleFactor=1.1,
                minNeighbors=4
            )

            if len(faces) == 0:
                print(f"Warning: No face detected in {image_file}")
                continue

            for (x, y, width, height) in faces:

                face_region = image_array[
                    y:y + height,
                    x:x + width
                ]

                resized_face = cv2.resize(
                    face_region,
                    IMAGE_SIZE
                )

                predicted_id, confidence = recognizer.predict(
                    resized_face
                )

                if (
                    confidence < CONFIDENCE_THRESHOLD
                    and predicted_id in labels
                ):
                    predicted_name = labels[predicted_id].replace(
                        "_", " "
                    ).title()
                else:
                    predicted_name = "Unknown"

                print(
                    f"{image_file} -> Predicted: {predicted_name} "
                    f"| Confidence: {confidence:.2f}"
                )

        except Exception as error:
            print(
                f"Could not process {image_file}: {error}"
            )
