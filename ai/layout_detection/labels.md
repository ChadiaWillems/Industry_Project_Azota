# Layout Detection Labels

The layout detection model uses object detection with bounding boxes.

## Labels

- `candidate_id_region`
- `exam_code_region`
- `student_info_region`
- `mcq_region`
- `true_false_region`
- `numeric_region`
- `essay_region`
- `score_field_region`
- `page_registration_marker`

## Notes

We do not annotate individual bubbles for the first model.  
The goal is to detect semantic regions of the exam sheet.  
Bubble reading will be handled later with OpenCV inside the detected regions.