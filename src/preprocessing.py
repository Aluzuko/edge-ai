import numpy as np
from PIL import Image


class ImagePreprocessor:

    def __init__(self, target_size: tuple[int, int] = (64, 64)):
        self.target_size = target_size

    def load_image(self, path: str) -> np.ndarray:
        image = Image.open(path).convert("RGB")
        image = image.resize(self.target_size)
        return np.array(image)

    def normalise(self, image_array: np.ndarray) -> np.ndarray:
        x = (image_array / 255.0).astype(np.float32)
        mean = x.mean()
        std = x.std()
        return ((x - mean) / max(std, 1e-5)).astype(np.float32)
