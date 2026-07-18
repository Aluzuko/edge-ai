import json
import sys
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pyodbc import IntegrityError

from config import IMAGES_DIR
from database import DictConnection, get_db
from schemas import DeviceRegister, RequestCreate
from pydantic import BaseModel


class RangerCreate(BaseModel):
    name: str
    contact: str | None = None


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from cnn import CNN
from preprocessing import ImagePreprocessor

MODEL_PATH = "models/best2.npz"
MODEL_META_PATH = "models/latest_meta.json"

with open(MODEL_META_PATH) as _f:
    _meta = json.load(_f)
MODEL_CLASSES = _meta["classes"]

MODEL_VERSION = f"cnn_v1_fp32_epoch{_meta['epoch']}"
MODEL_ACCURACY = _meta.get("best_val_acc", _meta.get("val_acc"))

_cnn = CNN(num_classes=len(MODEL_CLASSES))
_cnn.load(MODEL_PATH)
_preprocessor = ImagePreprocessor(target_size=(64, 64))

_model_run_id_cache: int | None = None


def _get_or_create_model_run(db: DictConnection) -> int:
    row = db.execute(
        "SELECT model_run_id FROM model_runs WHERE model_version = ?",
        (MODEL_VERSION,),
    ).fetchone()
    if row is not None:
        return row["model_run_id"]

    dummy = np.zeros((64, 64, 3))
    n_runs = 20
    start = time.perf_counter()
    for _ in range(n_runs):
        _cnn.forward(dummy)
    avg_latency_ms = (time.perf_counter() - start) / n_runs * 1000

    size_kb = Path(MODEL_PATH).stat().st_size / 1024

    row = db.execute(
        """
        INSERT INTO model_runs (model_version, quantized, size_kb, avg_latency_ms, accuracy)
        OUTPUT INSERTED.model_run_id
        VALUES (?, 0, ?, ?, ?)
        """,
        (MODEL_VERSION, size_kb, avg_latency_ms, MODEL_ACCURACY),
    ).fetchone()
    db.commit()
    return row["model_run_id"]

app = FastAPI(title="Wildlife Detection & Request API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check(db: DictConnection = Depends(get_db)):
    row = db.execute("SELECT COUNT(*) AS count FROM species").fetchone()
    return {"status": "ok", "species_count": row["count"]}

@app.get("/species")
def list_species(db: DictConnection = Depends(get_db)):
    rows = db.execute("SELECT * FROM species ORDER BY name").fetchall()
    return [dict(r) for r in rows]


@app.get("/cameras")
def list_cameras(db: DictConnection = Depends(get_db)):
    rows = db.execute("SELECT * FROM cameras ORDER BY name").fetchall()
    return [dict(r) for r in rows]


@app.get("/rangers")
def list_rangers(db: DictConnection = Depends(get_db)):
    rows = db.execute("SELECT * FROM rangers ORDER BY name").fetchall()
    return [dict(r) for r in rows]


@app.post("/rangers", status_code=201)
def create_ranger(payload: RangerCreate, db: DictConnection = Depends(get_db)):
    row = db.execute(
        """
        INSERT INTO rangers (name, contact)
        OUTPUT INSERTED.*
        VALUES (?, ?)
        """,
        (payload.name, payload.contact),
    ).fetchone()
    db.commit()
    return dict(row)

@app.post("/requests", status_code=201)
def create_request(payload: RequestCreate, db: DictConnection = Depends(get_db)):
    try:
        cur = db.execute(
            """
            INSERT INTO requests (ranger_id, species_id, camera_id, status)
            OUTPUT INSERTED.request_id
            VALUES (?, ?, ?, 'pending')
            """,
            (payload.ranger_id, payload.species_id, payload.camera_id),
        )
        new_id = cur.fetchone()["request_id"]
        db.commit()
    except IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Invalid reference: {e}")

    return get_request_by_id(new_id, db)


@app.get("/requests")
def list_requests(
    ranger_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    db: DictConnection = Depends(get_db),
):
    query = "SELECT * FROM requests WHERE 1=1"
    params: list = []
    if ranger_id is not None:
        query += " AND ranger_id = ?"
        params.append(ranger_id)
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"

    rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@app.get("/requests/{request_id}")
def get_request_by_id(request_id: int, db: DictConnection = Depends(get_db)):
    row = db.execute(
        """
        SELECT
            r.*,
            s.name AS species_name,
            d.detection_id, d.confidence, d.created_at AS detected_at,
            i.file_path, i.captured_at,
            c.name AS camera_name, c.latitude, c.longitude
        FROM requests r
        JOIN species s ON s.species_id = r.species_id
        LEFT JOIN detections d ON d.detection_id = r.fulfilled_detection_id
        LEFT JOIN images i ON i.image_id = d.image_id
        LEFT JOIN cameras c ON c.camera_id = i.camera_id
        WHERE r.request_id = ?
        """,
        (request_id,),
    ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Request not found")

    return dict(row)


@app.patch("/requests/{request_id}/seen")
def mark_request_seen(request_id: int, db: DictConnection = Depends(get_db)):
    row = db.execute(
        """
        UPDATE requests
        SET status = 'seen'
        OUTPUT INSERTED.*
        WHERE request_id = ? AND status = 'pending'
        """,
        (request_id,),
    ).fetchone()

    if row is None:
        existing = db.execute(
            "SELECT status FROM requests WHERE request_id = ?", (request_id,)
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Request not found")
        raise HTTPException(
            status_code=400,
            detail=f"Request is not 'pending' (current status: '{existing['status']}')",
        )

    db.commit()
    return dict(row)

@app.get("/detections")
def list_detections(
    species_id: int | None = Query(default=None),
    since: datetime | None = Query(default=None),
    db: DictConnection = Depends(get_db),
):
    query = """
        SELECT det.*, s.name AS species_name, i.file_path, i.captured_at
        FROM detections det
        JOIN species s ON s.species_id = det.species_id
        JOIN images i ON i.image_id = det.image_id
        WHERE 1=1
    """
    params: list = []
    if species_id is not None:
        query += " AND det.species_id = ?"
        params.append(species_id)
    if since is not None:
        query += " AND det.created_at >= ?"
        params.append(since)
    query += " ORDER BY det.created_at DESC"

    rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]

@app.post("/images", status_code=201)
def upload_image(
    camera_id: int = Form(...),
    file: UploadFile = File(...),
    db: DictConnection = Depends(get_db),
):
    camera = db.execute(
        "SELECT camera_id FROM cameras WHERE camera_id = ?", (camera_id,)
    ).fetchone()
    if camera is None:
        raise HTTPException(status_code=400, detail="Unknown camera_id")

    ext = Path(file.filename or "capture.jpg").suffix or ".jpg"
    camera_dir = IMAGES_DIR / str(camera_id)
    camera_dir.mkdir(exist_ok=True)

    filename = f"{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}{ext}"
    dest_path = camera_dir / filename
    dest_path.write_bytes(file.file.read())

    relative_path = f"{camera_id}/{filename}"
    row = db.execute(
        """
        INSERT INTO images (camera_id, file_path, captured_at)
        OUTPUT INSERTED.*
        VALUES (?, ?, GETDATE())
        """,
        (camera_id, relative_path),
    ).fetchone()
    db.commit()

    return dict(row)


@app.get("/images")
def list_images(
    unprocessed_only: bool = Query(default=False),
    db: DictConnection = Depends(get_db),
):
    query = """
        SELECT i.*, c.name AS camera_name
        FROM images i
        JOIN cameras c ON c.camera_id = i.camera_id
    """
    if unprocessed_only:
        query += """
            LEFT JOIN detections d ON d.image_id = i.image_id
            WHERE d.detection_id IS NULL
        """
    query += " ORDER BY i.captured_at DESC"

    rows = db.execute(query).fetchall()
    return [dict(r) for r in rows]


@app.get("/images/{image_id}/file")
def get_image_file(image_id: int, db: DictConnection = Depends(get_db)):

    row = db.execute(
        "SELECT file_path FROM images WHERE image_id = ?", (image_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Image record not found")

    full_path = IMAGES_DIR / row["file_path"]
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Image file missing on disk")

    return FileResponse(full_path)


@app.post("/images/{image_id}/detect", status_code=201)
def detect_image(image_id: int, db: DictConnection = Depends(get_db)):
    row = db.execute(
        "SELECT file_path FROM images WHERE image_id = ?", (image_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Image record not found")

    full_path = IMAGES_DIR / row["file_path"]
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Image file missing on disk")

    image_array = _preprocessor.load_image(str(full_path))
    processed = _preprocessor.normalise(image_array)

    inference_start = time.perf_counter()
    probs, _ = _cnn.forward(processed)
    inference_time_ms = (time.perf_counter() - inference_start) * 1000

    pred_idx = int(np.argmax(probs))
    predicted_class = MODEL_CLASSES[pred_idx]
    confidence = float(probs[pred_idx])

    species_row = db.execute(
        "SELECT species_id FROM species WHERE name = ?", (predicted_class,)
    ).fetchone()
    if species_row is None:
        raise HTTPException(
            status_code=500,
            detail=f"Model predicted class '{predicted_class}' which has no matching species row",
        )

    global _model_run_id_cache
    if _model_run_id_cache is None:
        _model_run_id_cache = _get_or_create_model_run(db)
    model_run_id = _model_run_id_cache

    cur = db.execute(
        """
        INSERT INTO detections (image_id, species_id, model_run_id, confidence, inference_time_ms, created_at)
        OUTPUT INSERTED.detection_id
        VALUES (?, ?, ?, ?, ?, GETDATE())
        """,
        (image_id, species_row["species_id"], model_run_id, confidence, inference_time_ms),
    )
    new_id = cur.fetchone()["detection_id"]
    db.commit()
    db.execute(
        """
        UPDATE requests
        SET fulfilled_detection_id = ?, fulfilled_at = GETDATE()
        WHERE species_id = ?
          AND status = 'pending'
          AND fulfilled_detection_id IS NULL
          AND (camera_id IS NULL OR camera_id = (
              SELECT camera_id FROM images WHERE image_id = ?
          ))
        """,
        (new_id, species_row["species_id"], image_id),
    )
    db.commit()

    detection_row = db.execute(
        """
        SELECT det.*, s.name AS species_name
        FROM detections det
        JOIN species s ON s.species_id = det.species_id
        WHERE det.detection_id = ?
        """,
        (new_id,),
    ).fetchone()
    return dict(detection_row)


@app.get("/model-runs")
def list_model_runs(db: DictConnection = Depends(get_db)):
    rows = db.execute(
        "SELECT * FROM model_runs ORDER BY created_at"
    ).fetchall()
    return [dict(r) for r in rows]

@app.post("/devices", status_code=201)
def register_device(payload: DeviceRegister, db: DictConnection = Depends(get_db)):
    try:
        db.execute(
            """
            MERGE devices AS target
            USING (SELECT ? AS fcm_token) AS source
            ON target.fcm_token = source.fcm_token
            WHEN MATCHED THEN
                UPDATE SET ranger_id = ?, platform = ?, last_active_at = GETDATE()
            WHEN NOT MATCHED THEN
                INSERT (ranger_id, fcm_token, platform) VALUES (?, ?, ?);
            """,
            (
                payload.fcm_token,
                payload.ranger_id, payload.platform,
                payload.ranger_id, payload.fcm_token, payload.platform,
            ),
        )
        db.commit()
    except IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Invalid reference: {e}")

    row = db.execute(
        "SELECT * FROM devices WHERE fcm_token = ?", (payload.fcm_token,)
    ).fetchone()
    return dict(row)