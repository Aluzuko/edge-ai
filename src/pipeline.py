import os
import time
import random
import json
from datetime import datetime
import numpy as np
from preprocessing import ImagePreprocessor
from cnn import CNN


class Pipeline:

    def __init__(
        self,
        data_dir: str,
        checkpoint_dir: str = "checkpoints",
        target_size: tuple[int, int] = (64, 64),
        num_filters: int = 8,
        num_filters2: int | None = None,
        kernel_size: int = 3,
        hidden_dim: int = 32,
        epochs: int = 200,
        lr: float = 0.001,
        batch_size: int = 16,
        max_hours: float | None = None,
        seed: int = 42,
        dropout_rate: float = 0.3,
        weight_decay: float = 1e-4,
    ):
        self.data_dir = data_dir
        self.checkpoint_dir = checkpoint_dir
        self.epochs = epochs
        self.lr = lr
        self.batch_size = batch_size
        self.max_hours = max_hours
        self.weight_decay = weight_decay
        self.preprocessor = ImagePreprocessor(target_size=target_size)
        random.seed(seed)

        self.run_name = datetime.utcnow().strftime("run_%Y%m%dT%H%M%SZ")
        self.run_dir = os.path.join(self.checkpoint_dir, self.run_name)
        os.makedirs(self.run_dir, exist_ok=True)

        train_root = os.path.join(data_dir, "train")
        self.classes = sorted(
            d for d in os.listdir(train_root) if os.path.isdir(os.path.join(train_root, d))
        )
        if not self.classes:
            raise ValueError(f"No class folders found under {train_root}")
        self.class_to_idx = {c: i for i, c in enumerate(self.classes)}
        print(f"Classes ({len(self.classes)}): {self.classes}")

        self.cnn = CNN(num_classes=len(self.classes), num_filters=num_filters,
                       kernel_size=kernel_size, hidden_dim=hidden_dim, seed=seed,
                       dropout_rate=dropout_rate, num_filters2=num_filters2)

        self.best_val_acc = 0.0

    def _save_checkpoint(self, epoch, val_acc):
        self.cnn.save(os.path.join(self.run_dir, "latest.npz"))

        meta = {
            "epoch": epoch,
            "val_acc": val_acc,
            "best_val_acc": self.best_val_acc,
            "classes": self.classes,
            "latest_file": "latest.npz",
            "run": self.run_name,
        }

        if val_acc > self.best_val_acc:
            self.best_val_acc = val_acc
            self.cnn.save(os.path.join(self.run_dir, "best.npz"))
            meta["best_val_acc"] = val_acc
            meta["best_file"] = "best.npz"
            print(f"  -> new best model saved (val accuracy {val_acc:.2%}) in run {self.run_name}")

        with open(os.path.join(self.run_dir, "latest_meta.json"), "w") as f:
            json.dump(meta, f)

    def _load_split(self, split: str) -> list[tuple[np.ndarray, int]]:
        data = []
        for class_name in self.classes:
            folder = os.path.join(self.data_dir, split, class_name)
            if not os.path.exists(folder):
                continue
            label_idx = self.class_to_idx[class_name]
            for filename in os.listdir(folder):
                if filename.lower().endswith((".jpg", ".jpeg")):
                    image = self.preprocessor.load_image(os.path.join(folder, filename))
                    data.append((self.preprocessor.normalise(image), label_idx))

        if not data:
            raise ValueError(f"No images found for split '{split}' under {self.data_dir}")
        return data

    def train(self):
        train_data = self._load_split("train")
        val_data = self._load_split("val")
        print(f"Train: {len(train_data)} images, Val: {len(val_data)} images")

        log_file = open(os.path.join(self.run_dir, "train_log.csv"), "w")
        log_file.write("epoch,avg_loss,val_accuracy,elapsed_seconds\n")

        run_start = time.time()

        for epoch in range(1, self.epochs + 1):
            if self.max_hours is not None and (time.time() - run_start) / 3600 >= self.max_hours:
                print(f"Reached max_hours={self.max_hours}, stopping before epoch {epoch}.")
                break

            epoch_start = time.time()
            random.shuffle(train_data)
            total_loss = 0.0

            for batch_start in range(0, len(train_data), self.batch_size):
                batch = train_data[batch_start:batch_start + self.batch_size]

                accumulated = None
                for image, label_idx in batch:
                    probs, cache = self.cnn.forward(image, training=True)
                    total_loss += self.cnn.loss(probs, label_idx)
                    grads = self.cnn.gradients(cache, label_idx)

                    if accumulated is None:
                        accumulated = grads
                    else:
                        for key in accumulated:
                            accumulated[key] = accumulated[key] + grads[key]

                for key in accumulated:
                    accumulated[key] = accumulated[key] / len(batch)
                self.cnn.apply_gradients(accumulated, self.lr, weight_decay=self.weight_decay)

            avg_loss = total_loss / len(train_data)
            val_acc = self.evaluate(val_data)
            elapsed = time.time() - epoch_start

            print(f"Epoch {epoch}/{self.epochs} — loss: {avg_loss:.4f} — "
                  f"val accuracy: {val_acc:.2%} — {elapsed:.1f}s")
            log_file.write(f"{epoch},{avg_loss:.6f},{val_acc:.6f},{elapsed:.1f}\n")
            log_file.flush()

            self._save_checkpoint(epoch, val_acc)

        log_file.close()
        print(f"\nTraining finished. Best val accuracy: {self.best_val_acc:.2%}")

    def evaluate(self, data: list[tuple[np.ndarray, int]]) -> float:
        correct = 0
        for image, label_idx in data:
            probs, _ = self.cnn.forward(image)
            if int(np.argmax(probs)) == label_idx:
                correct += 1
        return correct / len(data)

    def test(self):
        test_data = self._load_split("test")
        n = len(self.classes)
        confusion = np.zeros((n, n), dtype=int)

        for image, label_idx in test_data:
            probs, _ = self.cnn.forward(image)
            pred_idx = int(np.argmax(probs))
            confusion[label_idx, pred_idx] += 1

        accuracy = np.trace(confusion) / confusion.sum()
        print("\nTest Results")
        print(f"Overall accuracy: {accuracy:.2%}\n")
        print("Per-class precision / recall / F1:")
        for i, class_name in enumerate(self.classes):
            tp = confusion[i, i]
            fp = confusion[:, i].sum() - tp
            fn = confusion[i, :].sum() - tp
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            print(f"  {class_name:12s} precision {precision:.2%}  recall {recall:.2%}  f1 {f1:.2%}")

        print("\nConfusion matrix (rows=actual, cols=predicted):")
        header = "".join(f"{c[:8]:>10s}" for c in self.classes)
        print(" " * 12 + header)
        for i, class_name in enumerate(self.classes):
            row = "".join(f"{confusion[i, j]:>10d}" for j in range(n))
            print(f"{class_name[:12]:12s}{row}")
