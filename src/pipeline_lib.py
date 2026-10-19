import os

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.model_selection import train_test_split
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SRC_DIR, "..", "data")

IMAGE_SIZE = (128, 128)
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp")


def build_dataframe(data_dir=DATA_DIR):
    images = []

    for class_name in sorted(os.listdir(data_dir)):
        class_folder = os.path.join(data_dir, class_name)

        if not os.path.isdir(class_folder):
            continue

        for filename in os.listdir(class_folder):
            if not filename.lower().endswith(IMAGE_EXTENSIONS):
                continue

            images.append({
                "image_path": os.path.join(class_folder, filename),
                "class": class_name,
            })

    return pd.DataFrame(images)


def split_dataset(df, random_state=42):
    train_df, temp_df = train_test_split(
        df,
        test_size=0.30,
        random_state=random_state,
        stratify=df["class"],
    )

    validation_df, test_df = train_test_split(
        temp_df,
        test_size=0.50,
        random_state=random_state,
        stratify=temp_df["class"],
    )

    return train_df, validation_df, test_df


def get_class_mapping(df):
    classes = sorted(df["class"].unique())
    class_to_number = {class_name: index for index, class_name in enumerate(classes)}
    return classes, class_to_number


def load_image(image_path, image_size=IMAGE_SIZE):
    with Image.open(image_path) as image:
        image = image.convert("RGB")
        image = image.resize(image_size)
        image_array = np.asarray(image, dtype=np.float32) / 255.0

    return image_array


def prepare_dataset(dataframe, class_to_number):
    X = []
    y = []

    for _, row in dataframe.iterrows():
        X.append(load_image(row["image_path"]))
        y.append(class_to_number[row["class"]])

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)