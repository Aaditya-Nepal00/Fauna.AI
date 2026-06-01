# FaunaAI

Camera-trap processing pipeline for WWF Nepal's tiger survey.

## What it does

Camera traps across Chitwan and Bardia produce thousands of images per survey cycle — most of them blank frames triggered by wind or shadows. FaunaAI ingests the raw images, filters out the noise, detects animals, classifies species down to Bengal Tiger, and surfaces behavioral anomalies to field teams through a live dashboard. The goal is to cut the weeks between raw capture and actionable data down to hours.

## Architecture

![FaunaAI architecture](docs/architecture/architecture.svg)

The diagram shows how images flow from upload through both pipeline layers into SQLite, with results streaming to the React dashboard in real time over SSE.

## How it works

Every image runs through two layers sequentially, coordinated by `PipelineOrchestrator`.

**Layer 1 — FrameGuard** handles triage. The primary detector is MegaDetectorV6 (`MDV6-yolov9-c` via PytorchWildlife), which is purpose-built for camera-trap imagery and handles dense canopy, night IR, and cluttered backgrounds well. YOLO26n is available as a fallback via `DETECTOR_BACKEND=yolo`. Night images get CLAHE preprocessing before detection to recover detail from underexposed IR frames.

When an animal is detected, the bounding box crop goes to an EfficientNet-B0 (ImageNet weights) classifier. If the top prediction is class 292 (*tiger, Panthera tigris*), the frame is labeled **TIGER** and a second EfficientNet-B0 — fine-tuned for two-class flank orientation — determines whether the animal's left or right side is visible. That flank label feeds individual re-ID from stripe patterns. Blur is evaluated on the crop, not the whole image, with separate thresholds for night and day (IR sensors naturally produce lower Laplacian variance).

Every frame exits FrameGuard with one of five labels: **TIGER**, **OTHER_WILDLIFE**, **HUMAN**, **NON_OBJECT**, or **BLUR**.

**Layer 2 — SpeciesID** only runs on `OTHER_WILDLIFE` frames. Tiger and human are already resolved upstream. It classifies through an EfficientNet-B4 fine-tuned on Nepal fauna (Bengal Tiger, Greater One-horned Rhinoceros, Snow Leopard, Red Panda, Clouded Leopard, Asian Elephant, Gaur, Sambar Deer, Indian Leopard, Himalayan Black Bear, Sloth Bear, Nilgai). Without production weights it falls back to deterministic demo mode seeded on the filename hash — same image always returns the same result.

**After the batch — PulseScan** runs statistical analysis across all detections: 2-hour activity windows, 30-day rolling baselines per camera per species, five anomaly types (sudden absence, frequency spike, activity time shift, group size collapse, new species appearance). No model weights — pure pandas and SciPy. Alerts are written to the database and appear in the dashboard's alert panel.

Progress streams to the dashboard in real time via SSE as each image completes. PulseScan fires after the last image in the batch.

## Stack

**Backend** — Python 3.11, FastAPI, SQLAlchemy async, aiosqlite, PyTorch 2.3, TorchVision, Ultralytics, PytorchWildlife, OpenCV, NumPy, pandas, SciPy, sse-starlette, watchdog

**Frontend** — React 18, React Router 6, Vite 5

**DB** — SQLite via aiosqlite

## Getting started

**Backend**

```bash
cd backend
pip install -r requirements.txt
pip install PytorchWildlife      # not in requirements.txt — needed for MegaDetector
python run.py
```

API starts at `http://localhost:8000`. On first run it creates `fauna.db` and all required data directories automatically.

> To skip MegaDetector and avoid the weights download, set `DETECTOR_BACKEND=yolo` in a `.env` file inside `backend/`. YOLO26n is used instead.

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Dashboard runs at `http://localhost:5173`.

**Folder watcher** (optional)

```bash
cd backend
python -m app.watcher <survey_id> <camera_id> <path/to/watch/folder>
```

Drop an image into the watched folder and it runs through the full pipeline immediately, printing results to console. Useful for field demos where you want a live feed without the upload UI.

## Model weights and data

The pipeline runs in demo mode without any weights installed. Predictions are deterministic (seeded on filename hash), so the full UI behaves consistently during development.

To enable real inference, place these files in `backend/models/weights/`:

- `species_id.pt` — EfficientNet-B4 fine-tuned on Nepal fauna (Layer 2)
- `flank_classifier.pt` — EfficientNet-B0 fine-tuned for tiger flank orientation (Layer 1)

MegaDetectorV6 weights (`MDV6-yolov9-c.pt`) are downloaded automatically by PytorchWildlife on first startup and cached in your PyTorch hub directory.

The `data/` directory and all raw/processed images are not in the repo. The server creates `backend/data/raw/`, `backend/data/processed/`, and `backend/data/review_queue/` on startup automatically.

## What's not done yet

- Real EfficientNet-B4 inference in SpeciesID — `_real_predict()` currently raises `NotImplementedError`
- Individual tiger re-ID from flank crops — crops are saved to `backend/data/crops/` but the stripe-matching pipeline isn't built yet
