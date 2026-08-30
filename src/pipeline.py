import os
import time
import random
import json
import shutil
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
        self.preprocessor = ImagePreprocessor(target_size=target_size, seed=seed)
        random.seed(seed)

        os.makedirs(checkpoint_dir, exist_ok=True)

        # Move legacy timestamped checkpoint files into an import folder so
        # the checkpoint root does not accumulate many timestamped files.
        legacy_ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        imported_dir = os.path.join(checkpoint_dir, f"imported_runs_{legacy_ts}")
        moved_any = False
        for fname in os.listdir(checkpoint_dir):
            # skip canonical files and run folders
            if fname in ("latest.npz", "best.npz", "latest_meta.json"):
                continue
            full = os.path.join(checkpoint_dir, fname)
            if os.path.isfile(full) and (fname.startswith("latest_") or fname.startswith("best_") or fname == "train_log.csv"):
                os.makedirs(imported_dir, exist_ok=True)
                try:
                    shutil.move(full, os.path.join(imported_dir, fname))
                    moved_any = True
                except Exception:
                    pass
        if moved_any:
            print(f"Moved legacy checkpoint files into {imported_dir}")

        # create a dedicated folder for this training run
        self.run_name = datetime.utcnow().strftime("run_%Y%m%dT%H%M%SZ")
        self.run_dir = os.path.join(self.checkpoint_dir, self.run_name)
        os.makedirs(self.run_dir, exist_ok=True)

        # If the run folder already contains timestamped files from older
        # runs, move them into an `archived` subfolder to avoid clutter.
        archived_dir = os.path.join(self.run_dir, "archived")
        moved = False
        for fname in os.listdir(self.run_dir):
            if fname.startswith("latest_") or fname.startswith("best_"):
                os.makedirs(archived_dir, exist_ok=True)
                try:
                    shutil.move(os.path.join(self.run_dir, fname), os.path.join(archived_dir, fname))
                    moved = True
                except Exception:
                    pass
        if moved:
            print(f"Moved legacy run-local checkpoint files into {archived_dir}")

        # keep track of the previous best file for this run so we can delete it
        self._prev_best_path: str | None = None
        self._prev_best_ts: str | None = None

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

        self.start_epoch = 1
        self.best_val_acc = 0.0

    def _maybe_resume(self):
        # resume functionality removed: Pipeline starts fresh for each run
        return

    def _save_checkpoint(self, epoch, val_acc):
        # save latest checkpoint into the run folder (use fixed name)
        latest_run_path = os.path.join(self.run_dir, "latest.npz")
        self.cnn.save(latest_run_path)
        # Do not create canonical copies at checkpoint root; keep files in run folder only

        meta = {
            "epoch": epoch,
            "val_acc": val_acc,
            "best_val_acc": self.best_val_acc,
            "classes": self.classes,
            "latest_file": os.path.basename(latest_run_path),
            "run": self.run_name,
        }
        # write run-local meta only
        with open(os.path.join(self.run_dir, "latest_meta.json"), "w") as f:
            json.dump(meta, f)

        # if this is a new best, save into a consistent best.npz inside the run folder
        if val_acc > self.best_val_acc:
            self.best_val_acc = val_acc
            best_run_path = os.path.join(self.run_dir, "best.npz")
            # save will overwrite any existing run-local best
            self.cnn.save(best_run_path)

            meta["best_file"] = os.path.basename(best_run_path)
            # update run-local meta with best file name
            with open(os.path.join(self.run_dir, "latest_meta.json"), "w") as f:
                json.dump(meta, f)
            print(f"  -> new best model saved (val accuracy {val_acc:.2%}) in run {self.run_name}")

    def _load_split(self, split: str, augment: bool = False) -> list[tuple[np.ndarray, int]]:
        data = []
        for class_name in self.classes:
            folder = os.path.join(self.data_dir, split, class_name)
            if not os.path.exists(folder):
                continue
            label_idx = self.class_to_idx[class_name]
            for filename in os.listdir(folder):
                if filename.lower().endswith((".jpg", ".jpeg")):
                    path = os.path.join(folder, filename)
                    if augment:
                        image = self.preprocessor.load_image(path, augment=True)
                        data.append((image, label_idx))
                    else:
                        image = self.preprocessor.load_image(path)
                        processed = self.preprocessor.normalise(image)
                        data.append((processed, label_idx))

        if not data:
            raise ValueError(f"No images found for split '{split}' under {self.data_dir}")
        return data

    def train(self):
        train_data = self._load_split("train", augment=True)
        val_data = self._load_split("val")
        print(f"Train: {len(train_data)} images, Val: {len(val_data)} images")

        log_path = os.path.join(self.run_dir, "train_log.csv")
        log_is_new = not os.path.exists(log_path)
        log_file = open(log_path, "a")
        if log_is_new:
            log_file.write("epoch,avg_loss,val_accuracy,elapsed_seconds\n")

        run_start = time.time()

        for epoch in range(self.start_epoch, self.epochs + 1):
            if self.max_hours is not None and (time.time() - run_start) / 3600 >= self.max_hours:
                print(f"Reached max_hours={self.max_hours}, stopping before epoch {epoch}.")
                break

            epoch_start = time.time()
            random.shuffle(train_data)
            total_loss = 0.0

            for batch_start in range(0, len(train_data), self.batch_size):
                batch = train_data[batch_start:batch_start + self.batch_size]

                accumulated = None
                for image_big, label_idx in batch:
                    # Fresh random crop/flip/brightness jitter each epoch,
                    # then forward with dropout active (training=True).
                    augmented = self.preprocessor.augment_array(image_big)
                    image = self.preprocessor.normalise(augmented)

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

        # No canonical copies are kept; run-local files are authoritative.

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