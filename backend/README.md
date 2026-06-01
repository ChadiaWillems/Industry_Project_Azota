# Backend

This folder will contain the backend API for the Azota exam grading system.

## Purpose

The backend will connect the frontend with the AI/computer vision pipeline.

It will be responsible for:

- Receiving uploaded exam sheet images
- Saving input files and generated outputs
- Calling the AI pipeline for standardization, layout detection, and answer extraction
- Returning structured results to the frontend
- Managing grading logic
- Supporting manual review and correction later

## Planned API Flow

```text
Frontend uploads exam image
        ↓
Backend receives and stores image
        ↓
Backend calls AI pipeline
        ↓
AI returns detected regions and extracted answers
        ↓
Backend compares answers with answer key
        ↓
Backend returns result to frontend