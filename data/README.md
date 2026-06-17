# Data

Most of this folder is gitignored (raw photos, standardized outputs, Roboflow datasets, training caches).

## What is committed

- `data/evaluation/unseen_templates/` — 3 raw + 3 standardized blank exam sheets used to evaluate YOLO predictions on unseen layouts
- `data/standardized_smoke_test/` — one image in all four standardization output variants (corrected, readable, binary, debug) for quick pipeline sanity checks
- `data/test_filled/` — folder structure only (`.gitkeep`); drop filled student exam photos here to run the full OMR pipeline

## What is not committed

- `data/input/` — drop raw photos here to run standardization
- `data/standardized/` — standardization output (corrected, readable, binary, debug variants)
- `data/roboflow/` — Roboflow YOLOv8 dataset exports (v1 and v2)
