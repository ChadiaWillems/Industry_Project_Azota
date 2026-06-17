# Frontend

Streamlit UI for the Azota exam grading system. Entry point is `app_streamlit.py` in the project root.

## Pages

- **Camera page** — two tabs: upload a blank sheet to generate an answer key template, or upload a student submission to grade it
- **Preview page** — shows the standardized image before running the full pipeline
- **Results page** — detection image, graded bubble image, per-section scores (MCQ / T/F / Numeric), editable essay score, and total
- **Edit result page** — teacher can correct the essay score and save to the database

## Running

```bash
streamlit run app_streamlit.py
```

Requires the `azota-yolo` conda environment (ultralytics + streamlit).
