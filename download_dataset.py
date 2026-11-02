from sklearn.datasets import fetch_lfw_people
import os
import cv2

# Download dataset
lfw = fetch_lfw_people(min_faces_per_person=20, resize=0.5)

# Create dataset folder
os.makedirs("dataset", exist_ok=True)

for i, name in enumerate(lfw.target_names[:7]):  # Pick first 7 people
    person_folder = os.path.join("dataset", name.replace(" ", "_"))
    os.makedirs(person_folder, exist_ok=True)

    images = lfw.images[lfw.target == i]

    for j, img in enumerate(images[:20]):  # Save 20 images per person
        img = (img * 255).astype("uint8")
        cv2.imwrite(os.path.join(person_folder, f"{j}.jpg"), img)

print("Dataset downloaded and saved into dataset/ folder")
