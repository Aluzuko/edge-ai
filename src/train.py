import os

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Conv2D, Dense, Dropout, Flatten, Input, MaxPooling2D

from pipeline_lib import (
    IMAGE_SIZE,
    SRC_DIR,
    build_dataframe,
    get_class_mapping,
    load_image,
    prepare_dataset,
    split_dataset,
)

EPOCHS = 20
BATCH_SIZE = 32
MODEL_PATH = os.path.join(SRC_DIR, "wildlife_cnn.keras")


def build_model(num_classes):
    model = Sequential([
        Input(shape=(IMAGE_SIZE[0], IMAGE_SIZE[1], 3)),

        Conv2D(32, (3, 3), activation="relu"),
        MaxPooling2D((2, 2)),

        Conv2D(64, (3, 3), activation="relu"),
        MaxPooling2D((2, 2)),

        Conv2D(128, (3, 3), activation="relu"),
        MaxPooling2D((2, 2)),

        Flatten(),
        Dense(128, activation="relu"),
        Dropout(0.5),
        Dense(num_classes, activation="softmax"),
    ])

    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    return model


def plot_history(history):
    plt.figure()
    plt.plot(history.history["accuracy"])
    plt.plot(history.history["val_accuracy"])
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.legend(["Training", "Validation"])
    plt.title("Accuracy")

    plt.figure()
    plt.plot(history.history["loss"])
    plt.plot(history.history["val_loss"])
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.legend(["Training", "Validation"])
    plt.title("Loss")

    plt.show()


def predict_image(model, image_path, classes):
    image = load_image(image_path)
    image = np.expand_dims(image, axis=0)
    prediction = model.predict(image, verbose=0)[0]
    predicted_class = classes[int(np.argmax(prediction))]
    confidence = float(np.max(prediction))
    return predicted_class, confidence


def main():
    df = build_dataframe()
    print(df.head())
    print(df["class"].value_counts())
    print("Total images:", df.shape[0])
    train_df, validation_df, test_df = split_dataset(df)
    print("Training:", len(train_df))
    print("Validation:", len(validation_df))
    print("Testing:", len(test_df))
    classes, class_to_number = get_class_mapping(df)
    print(class_to_number)
    X_train, y_train = prepare_dataset(train_df, class_to_number)
    X_validation, y_validation = prepare_dataset(validation_df, class_to_number)
    X_test, y_test = prepare_dataset(test_df, class_to_number)

    print(X_train.shape, y_train.shape)
    print(X_validation.shape, y_validation.shape)
    print(X_test.shape, y_test.shape)
    model = build_model(num_classes=len(classes))
    model.summary()
    history = model.fit(
        X_train,
        y_train,
        validation_data=(X_validation, y_validation),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
    )
    test_loss, test_accuracy = model.evaluate(X_test, y_test)
    print("Test loss:", test_loss)
    print("Test accuracy:", test_accuracy)
    model.save(MODEL_PATH)
    print("Model saved to", MODEL_PATH)
    sample_path = test_df.iloc[0]["image_path"]
    predicted_class, confidence = predict_image(model, sample_path, classes)
    print(f"Sample: {sample_path}")
    print(f"Actual: {test_df.iloc[0]['class']}  Predicted: {predicted_class} ({confidence:.2%})")
    plot_history(history)


if __name__ == "__main__":
    main()