# Layout Detection Baseline Notes

Baseline model:

- Model: YOLOv8s
- Weights: models/baselines/yolov8s_layout_v1/best.pt
- Evaluation folder: data/evaluation/unseen_templates/readable
- Prediction run: baseline_unseen_v1

## Unseen template 1

Problems observed:

- Detects more than 4 registration markers.
- Detects internal black squares / small markers as registration markers.
- Detects the instruction area as student_info_region.
- Detects student_info_region twice.
- Detects a low-confidence true_false_region on a section that is not a true/false region.
- Some region labels overlap visually and make the output messy.

## Unseen template 2

Problems observed:

- MCQ area is detected as one large mcq_region instead of separate MCQ blocks.
- Only one main registration marker is detected clearly.
- Candidate ID and exam code are confused / duplicated.
- Candidate_id_region appears where exam_code_region should be.

## Unseen template 3

Problems observed:

- Some numeric regions are predicted as mcq_region.
- More than 4 registration markers are detected.
- Candidate ID / exam code separation is not fully reliable.
- MCQ and numeric layouts are visually similar, causing confusion.

## Main error categories

1. Registration marker problem

The model detects too many black squares. We only want the 4 main outer page markers.

2. Student info / instruction confusion

The model sometimes thinks instruction text is student_info_region.

3. Candidate ID / exam code confusion

These two regions look very similar, so the model confuses them.

4. MCQ / numeric confusion

Both contain bubble grids, so numeric regions can be predicted as MCQ.

5. MCQ block splitting

The model sometimes detects one big MCQ area instead of separate MCQ blocks.

## Improvement plan

Short term:

- Add post-processing rules after YOLO prediction.
- Use class-specific confidence thresholds.
- Keep only 4 corner registration markers.
- Keep only one student_info_region.
- Keep only one candidate_id_region and one exam_code_region.
- Remove low-confidence wrong detections.

Dataset improvement:

- Check and clean annotations.
- Make registration_marker labels strict.
- Make MCQ annotation style consistent.
- Add hard examples where instructions are not labeled as student info.
- Add examples where numeric regions are correctly labeled as numeric_region.

Model experiment later:

- Retrain YOLOv8s on cleaned dataset.
- Only after that, compare with YOLOv8m.