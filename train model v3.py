import os
import cv2
import numpy as np
from PIL import Image
import pickle

DATASET_DIR = "dataset"
IMAGE_SIZE = (200, 200)  # Resize all faces to same size

recognizer = cv2.face.LBPHFaceRecognizer_create()

current_id = 0
label_ids = {}
x_train = []
y_labels = []

print("🔍 Loading images for training...\n")

for root, dirs, files in os.walk(DATASET_DIR):
    for file in files:
        if file.lower().endswith(("png", "jpg", "jpeg")):
            path = os.path.join(root, file)
            label = os.path.basename(root).replace(" ", "_").lower()

            if label not in label_ids:
                label_ids[label] = current_id
                current_id += 1

            id_ = label_ids[label]

            try:
                pil_image = Image.open(path).convert("L")  # grayscale
                image_array = np.array(pil_image, "uint8")

                # Resize image to fixed size
                resized_image = cv2.resize(image_array, IMAGE_SIZE)

                x_train.append(resized_image)
                y_labels.append(id_)

                print("✅ Added image for:", label)

            except Exception as e:
                print("⚠️ Could not process:", path, "| Error:", e)

print("\n📊 Total training images:", len(x_train))

if len(x_train) == 0:
    print("❌ No training images found. Check dataset folder.")
    exit()

# Save label mapping
with open("labels.pickle", "wb") as f:
    pickle.dump(label_ids, f)

# Train recognizer
print("🧠 Training model...")
recognizer.train(x_train, np.array(y_labels))

# Save trained model
recognizer.save("trainer.yml")

print("\n✅ Training complete!")
print("📁 Files created: trainer.yml, labels.pickle")
