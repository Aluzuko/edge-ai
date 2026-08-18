import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import numpy as np

from pipeline import Pipeline

if __name__ == "__main__":
    DATA_DIR = "../data_split"
    CHECKPOINT_DIR = "checkpoints"

    pipeline = Pipeline(
        data_dir=DATA_DIR,
        checkpoint_dir=CHECKPOINT_DIR,
        epochs=200,
        lr=0.001,
        batch_size=16,
        max_hours=8.0,
    )

    print("\nTraining\n")
    pipeline.train()

    best_path = os.path.join(CHECKPOINT_DIR, "best.npz")
    if os.path.exists(best_path):
        pipeline.cnn.load(best_path)
        dummy_input = np.zeros((64, 64, 3), dtype=np.float32)
        runs = 20
        start = time.perf_counter()
        for _ in range(runs):
            pipeline.cnn.forward(dummy_input)
        avg_latency_ms = (time.perf_counter() - start) / runs * 1000
        size_kb = os.path.getsize(best_path) / 1024

        payload = {
            "quantized": False,
            "size_kb": size_kb,
            "avg_latency_ms": avg_latency_ms,
            "accuracy": pipeline.best_val_acc,
            "model_version": getattr(pipeline, "run_name", None),
        }

        url = "http://127.0.0.1:8000/model-runs"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        log_path = os.path.join(CHECKPOINT_DIR, "model_run_post.log")
        try:
            with urllib.request.urlopen(req) as resp:
                status = resp.getcode()
                body = resp.read().decode("utf-8")
            entry = (
                f"{datetime.now(timezone.utc).isoformat()} POST {url}\n"
                f"Payload: {json.dumps(payload)}\n"
                f"Response code: {status}\n"
                f"Body: {body}\n\n"
            )
            with open(log_path, "a", encoding="utf-8") as lf:
                lf.write(entry)
            print(f"Posted model run to {url}: {status}")
        except urllib.error.HTTPError as e:
            # HTTPError has a response body we can log
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                err_body = "<no body>"
            entry = (
                f"{datetime.now(timezone.utc).isoformat()} POST {url} FAILED\n"
                f"Payload: {json.dumps(payload)}\n"
                f"HTTPError: {e.code} - {e.reason}\n"
                f"Body: {err_body}\n\n"
            )
            with open(log_path, "a", encoding="utf-8") as lf:
                lf.write(entry)
            print(f"Failed to post model run: HTTP {e.code} - {e.reason}")
            print(err_body)
        except urllib.error.URLError as e:
            entry = (
                f"{datetime.now(timezone.utc).isoformat()} POST {url} ERROR\n"
                f"Payload: {json.dumps(payload)}\n"
                f"URLError: {e.reason}\n\n"
            )
            with open(log_path, "a", encoding="utf-8") as lf:
                lf.write(entry)
            print(f"Failed to post model run: {e.reason}")
    else:
        print(f"Best model file not found at {best_path}, skipping model-run post.")

    print("\nEvaluating on test\n")
    pipeline.test()