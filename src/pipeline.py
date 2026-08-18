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
        kernel_size: int = 3,
        hidden_dim: int = 32,
        epochs: int = 200,
        lr: float = 0.001,
        batch_size: int = 16,
        max_hours: float | None = None,
        seed: int = 42,
    ):
        self.data_dir = data_dir
        self.checkpoint_dir = checkpoint_dir
        self.epochs = epochs
        self.lr = lr
        self.batch_size = batch_size
        self.max_hours = max_hours
        self.preprocessor = ImagePreprocessor(target_size=target_size)
        random.seed(seed)

        os.makedirs(checkpoint_dir, exist_ok=True)

        # create a dedicated folder for this training run
        self.run_name = datetime.utcnow().strftime("run_%Y%m%dT%H%M%SZ")
        self.run_dir = os.path.join(self.checkpoint_dir, self.run_name)
        os.makedirs(self.run_dir, exist_ok=True)

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
                        kernel_size=kernel_size, hidden_dim=hidden_dim, seed=seed)

        self.start_epoch = 1
        self.best_val_acc = 0.0
        self._maybe_resume()

    def _maybe_resume(self):
        latest_path = os.path.join(self.checkpoint_dir, "latest.npz")
        meta_path = os.path.join(self.checkpoint_dir, "latest_meta.json")
        if os.path.exists(latest_path) and os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            if meta.get("classes") != self.classes:
                print("WARNING: checkpoint's class list doesn't match current data — "
                      "starting fresh instead of resuming.")
                return
            self.cnn.load(latest_path)
            self.start_epoch = meta["epoch"] + 1
            self.best_val_acc = meta.get("best_val_acc", 0.0)
            # If a timestamped best file was recorded in metadata, ensure a
            # canonical best.npz exists so downstream code (e.g. post-run
            # reporting) can find it.
            best_meta_name = meta.get("best_file")
            best_path = os.path.join(self.checkpoint_dir, "best.npz")
            if best_meta_name:
                # candidate may live inside a run folder; prefer absolute path if provided
                candidate = os.path.join(self.checkpoint_dir, best_meta_name)
                # if the metadata referred to a file inside a run folder, that path
                # will start with the run folder name. Try that too.
                if not os.path.exists(candidate):
                    candidate = os.path.join(self.checkpoint_dir, meta.get("run", ""), best_meta_name)
                if os.path.exists(candidate) and not os.path.exists(best_path):
                    try:
                        shutil.copy2(candidate, best_path)
                    except Exception:
                        pass

            print(f"Resumed from checkpoint: epoch {meta['epoch']}, "
                  f"best val accuracy so far {self.best_val_acc:.2%}")

    def _save_checkpoint(self, epoch, val_acc):
        # save a timestamped latest checkpoint and update canonical latest.npz
        ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        latest_ts_path = os.path.join(self.run_dir, f"latest_{ts}.npz")
        self.cnn.save(latest_ts_path)
        latest_path = os.path.join(self.checkpoint_dir, "latest.npz")
        try:
            shutil.copy2(latest_ts_path, latest_path)
        except Exception:
            # best-effort: if copy fails, still keep the timestamped file
            pass

        meta = {
            "epoch": epoch,
            "val_acc": val_acc,
            "best_val_acc": self.best_val_acc,
            "classes": self.classes,
            "latest_file": os.path.basename(latest_ts_path),
            "run": self.run_name,
        }
        # write run-local meta and a canonical meta at checkpoint root
        with open(os.path.join(self.run_dir, "latest_meta.json"), "w") as f:
            json.dump(meta, f)
        with open(os.path.join(self.checkpoint_dir, "latest_meta.json"), "w") as f:
            json.dump(meta, f)

        # if this is a new best, save a timestamped best file and update canonical best.npz
        if val_acc > self.best_val_acc:
            self.best_val_acc = val_acc
            best_ts_path = os.path.join(self.run_dir, f"best_{ts}.npz")
            self.cnn.save(best_ts_path)

            # delete previous best for this run (if any) to keep run folder tidy
            try:
                if self._prev_best_path and os.path.exists(self._prev_best_path):
                    os.remove(self._prev_best_path)
            except Exception:
                pass
            self._prev_best_path = best_ts_path
            self._prev_best_ts = ts

            # update canonical best at checkpoint root
            best_path = os.path.join(self.checkpoint_dir, "best.npz")
            try:
                shutil.copy2(best_ts_path, best_path)
            except Exception:
                pass

            meta["best_file"] = os.path.basename(best_ts_path)
            # update run-local and canonical meta with best file name
            with open(os.path.join(self.run_dir, "latest_meta.json"), "w") as f:
                json.dump(meta, f)
            with open(os.path.join(self.checkpoint_dir, "latest_meta.json"), "w") as f:
                json.dump(meta, f)
            print(f"  -> new best model saved (val accuracy {val_acc:.2%}) in run {self.run_name}")

    def _load_split(self, split: str) -> list[tuple[np.ndarray, int]]:
        data = []
        for class_name in self.classes:
            folder = os.path.join(self.data_dir, split, class_name)
            if not os.path.exists(folder):
                continue
            label_idx = self.class_to_idx[class_name]
            for filename in os.listdir(folder):
                if filename.lower().endswith((".jpg", ".jpeg")):
                    path = os.path.join(folder, filename)
                    image = self.preprocessor.load_image(path)
                    processed = self.preprocessor.normalise(image)
                    data.append((processed, label_idx))

        if not data:
            raise ValueError(f"No images found for split '{split}' under {self.data_dir}")
        return data

    def train(self):
        train_data = self._load_split("train")
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
                for image, label_idx in batch:
                    probs, cache = self.cnn.forward(image)
                    total_loss += self.cnn.loss(probs, label_idx)
                    grads = self.cnn.gradients(cache, label_idx)

                    if accumulated is None:
                        accumulated = grads
                    else:
                        for key in accumulated:
                            accumulated[key] = accumulated[key] + grads[key]

                for key in accumulated:
                    accumulated[key] = accumulated[key] / len(batch)
                self.cnn.apply_gradients(accumulated, self.lr)

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

        # Ensure there is a timestamped best file even if no new best was
        # discovered during this run. This creates `best_YYYYMMDDTHHMMSSZ.npz`
        # from the canonical `best.npz` (if present) and updates metadata.
        best_path = os.path.join(self.checkpoint_dir, "best.npz")
        if os.path.exists(best_path):
            try:
                ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
                best_ts_path = os.path.join(self.run_dir, f"best_{ts}.npz")
                shutil.copy2(best_path, best_ts_path)
                # update both run-local and canonical meta if present
                meta_path = os.path.join(self.run_dir, "latest_meta.json")
                try:
                    if os.path.exists(meta_path):
                        with open(meta_path) as f:
                            meta = json.load(f)
                        meta["best_file"] = os.path.basename(best_ts_path)
                        with open(meta_path, "w") as f:
                            json.dump(meta, f)
                    # also update canonical meta at root
                    root_meta = os.path.join(self.checkpoint_dir, "latest_meta.json")
                    if os.path.exists(root_meta):
                        with open(root_meta) as f:
                            rmeta = json.load(f)
                        rmeta["best_file"] = os.path.basename(best_ts_path)
                        with open(root_meta, "w") as f:
                            json.dump(rmeta, f)
                except Exception:
                    pass
            except Exception:
                pass

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