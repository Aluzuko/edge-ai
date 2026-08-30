import numpy as np
from PIL import Image


class ImagePreprocessor:

    def __init__(self, target_size: tuple[int, int] = (64, 64),
                 augment_scale: float = 1.25, seed: int = 42):
        self.target_size = target_size
        # How much larger than target_size to load images when augmenting,
        # so there's room for a random crop each epoch.
        self.augment_scale = augment_scale
        self._rng = np.random.default_rng(seed)

    def load_image(self, path: str, augment: bool = False) -> np.ndarray:
        image = Image.open(path).convert("RGB")
        if augment:
            tw, th = self.target_size
            big_size = (max(tw, int(round(tw * self.augment_scale))),
                        max(th, int(round(th * self.augment_scale))))
            image = image.resize(big_size)
        else:
            image = image.resize(self.target_size)
        return np.array(image)

    def augment_array(self, big_array: np.ndarray) -> np.ndarray:
        tw, th = self.target_size
        img = Image.fromarray(big_array)

        # random rotation (small angles -- animals stay upright in practice)
        angle = self._rng.uniform(-15, 15)
        img = img.rotate(angle, resample=Image.BILINEAR, expand=False)

        # random zoom: crop a random sub-box then resize to target
        H, W = img.size[1], img.size[0]
        zoom = self._rng.uniform(0.75, 1.0)
        ch, cw = int(H * zoom), int(W * zoom)
        y0 = int(self._rng.integers(0, max(H - ch, 0) + 1))
        x0 = int(self._rng.integers(0, max(W - cw, 0) + 1))
        img = img.crop((x0, y0, x0 + cw, y0 + ch)).resize((tw, th), Image.BILINEAR)

        crop = np.array(img)

        # random horizontal flip
        if self._rng.random() < 0.5:
            crop = crop[:, ::-1, :]

        crop = crop.astype(np.float32)

        # random brightness jitter
        crop = crop * (1.0 + self._rng.uniform(-0.3, 0.3))

        # random contrast jitter (around the image's own mean)
        mean = crop.mean()
        crop = (crop - mean) * (1.0 + self._rng.uniform(-0.3, 0.3)) + mean

        # random saturation jitter, and sometimes drop colour entirely so the
        # network can't rely on colour alone to separate the classes
        gray = crop.mean(axis=2, keepdims=True)
        if self._rng.random() < 0.15:
            crop = np.repeat(gray, 3, axis=2)
        else:
            sat = 1.0 + self._rng.uniform(-0.4, 0.4)
            crop = gray + (crop - gray) * sat

        return np.clip(crop, 0, 255).astype(np.uint8)

    def normalise(self, image_array: np.ndarray) -> np.ndarray:
        x = (image_array / 255.0).astype(np.float32)
        mean = x.mean()
        std = x.std()
        return ((x - mean) / max(std, 1e-5)).astype(np.float32)
