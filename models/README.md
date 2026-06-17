# Models

Model weights (`.pt`, `.onnx`, `.engine`) are gitignored due to file size.

## Current best model

```
runs/detect/runs/azota_layout/yolov8l_layout_v2/weights/best.pt
```

YOLOv8l trained on the v2 dataset (318 train / 20 valid / 7 test). mAP50=0.995, mAP50-95=0.858.

## Baseline (committed for reference)

`models/baselines/yolov8s_layout_v1/` — YOLOv8s on the v1 dataset. Confusion matrices and unseen-template predictions are kept to document the improvement from v1 to v2.
