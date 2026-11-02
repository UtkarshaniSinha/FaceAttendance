
import os
import pickle
from datetime import datetime

import cv2
import pandas as pd


# -----------------------------
# CONFIGURATION
# -----------------------------

DATASET_DIR = "dataset"
MODEL_FILE = "trainer.yml"
LABELS_FILE = "labels.pickle"
ATTENDANCE_FILE = "attendance.csv"

IMAGE_SIZE = (200, 200)
CONFIDENCE_THRESHOLD = 50


# -----------------------------
# LOAD TRAINED MODEL
# -----------------------------

if not os.path.isfile(MODEL_FILE):
    raise FileNotFoundError(
        f"Trained model not found: {MODEL_FILE}"
    )

if not os.path.isfile(LABELS_FILE):
    raise FileNotFoundError(
        f"Label file not found: {LABELS_FILE}"
    )

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read(MODEL_FILE)

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
# LOAD ATTENDANCE RECORDS
# -----------------------------

if os.path.isdir(ATTENDANCE_FILE):
    raise IsADirectoryError(
        f"{ATTENDANCE_FILE} is a directory. "
        "Rename or move that directory before running this script."
    )

if os.path.exists(ATTENDANCE_FILE):
    attendance_df = pd.read_csv(ATTENDANCE_FILE)
else:
    attendance_df = pd.DataFrame(
        columns=["Name", "Time"]
    )

required_columns = {"Name", "Time"}

if not required_columns.issubset(attendance_df.columns):
    raise ValueError(
        "Attendance CSV must contain Name and Time columns."
    )


# -----------------------------
# START WEBCAM
# -----------------------------

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    raise RuntimeError("Could not open the webcam.")

print("Webcam started. Press Q to quit.")


try:
    while True:

        success, frame = camera.read()

        if not success:
            print("Warning: Could not capture a webcam frame.")
            break

        gray_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        faces = face_cascade.detectMultiScale(
            gray_frame,
            scaleFactor=1.2,
            minNeighbors=5
        )

        for (x, y, width, height) in faces:

            face_region = gray_frame[
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

                name = labels[predicted_id].replace("_", " ").title()

                color = (0, 255, 0)

                # Check whether attendance is already recorded today.
                today = datetime.now().strftime("%Y-%m-%d")

                already_marked = (
                    (attendance_df["Name"] == name)
                    & attendance_df["Time"].astype(str).str.startswith(today)
                ).any()

                if not already_marked:

                    current_time = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                    new_record = pd.DataFrame(
                        [[name, current_time]],
                        columns=["Name", "Time"]
                    )

                    attendance_df = pd.concat(
                        [attendance_df, new_record],
                        ignore_index=True
                    )

                    try:
                        attendance_df.to_csv(
                            ATTENDANCE_FILE,
                            index=False
                        )

                        print(
                            f"Attendance marked for {name} "
                            f"at {current_time}"
                        )

                    except PermissionError:
                        attendance_df = attendance_df.iloc[:-1]
                        print(
                            "Warning: Could not save attendance. "
                            "Close the CSV file if it is open."
                        )

            else:
                name = "Unknown"
                color = (0, 0, 255)

            cv2.rectangle(
                frame,
                (x, y),
                (x + width, y + height),
                color,
                2
            )

            cv2.putText(
                frame,
                name,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                color,
                2
            )

        cv2.imshow("Face Attendance System", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    camera.release()
    cv2.destroyAllWindows()
    print("Webcam stopped.")
