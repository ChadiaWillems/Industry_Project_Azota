# ai/layout_detection/predict_yolo_layout.py

"""
Run prediction with a trained YOLO layout detection model.

This script saves:
1. Raw YOLO predictions
2. Post-processed / cleaned predictions

Example:

python ai/layout_detection/predict_yolo_layout.py --weights models/baselines/yolov8s_layout_v1/best.pt --source data/evaluation/unseen_templates/readable --conf 0.25 --imgsz 1024 --name baseline_unseen_v1_cleaned
"""

from pathlib import Path
import argparse
import sys

import cv2
from ultralytics import YOLO

from postprocess_layout import Detection, postprocess_detections


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run YOLO layout detection predictions."
    )

    parser.add_argument(
        "--weights",
        type=str,
        required=True,
        help="Path to trained model weights, usually best.pt.",
    )

    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Path to an image or folder of images.",
    )

    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Raw YOLO confidence threshold. Keep this low because post-processing applies class-specific thresholds later.",
    )

    parser.add_argument(
        "--imgsz",
        type=int,
        default=1024,
        help="Prediction image size.",
    )

    parser.add_argument(
        "--project",
        type=str,
        default="runs/azota_layout_predictions",
        help="Folder where prediction results will be saved.",
    )

    parser.add_argument(
        "--name",
        type=str,
        default="predict_v1",
        help="Name of this prediction run.",
    )

    parser.add_argument(
        "--device",
        type=str,
        default="0",
        help="Device to use. Use 0 for GPU or cpu for CPU.",
    )

    return parser.parse_args()


def yolo_result_to_detections(result) -> list[Detection]:
    """
    Convert one Ultralytics YOLO result into our Detection dataclass format.
    """
    detections = []

    if result.boxes is None:
        return detections

    names = result.names

    for box in result.boxes:
        class_id = int(box.cls[0].item())
        class_name = names[class_id]
        confidence = float(box.conf[0].item())

        x1, y1, x2, y2 = box.xyxy[0].tolist()

        detections.append(
            Detection(
                class_name=class_name,
                confidence=confidence,
                box=(x1, y1, x2, y2),
            )
        )

    return detections


def draw_detections(image, detections: list[Detection]):
    """
    Draw cleaned detections on an image.
    """
    output = image.copy()

    for det in detections:
        x1, y1, x2, y2 = [int(value) for value in det.box]

        label = f"{det.class_name} {det.confidence:.2f}"

        cv2.rectangle(
            output,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2,
        )

        cv2.putText(
            output,
            label,
            (x1, max(y1 - 8, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

    return output


def save_cleaned_txt(txt_path: Path, detections: list[Detection]):
    """
    Save cleaned detections in a simple readable text format.

    Format:
    class_name confidence x1 y1 x2 y2
    """
    with txt_path.open("w", encoding="utf-8") as file:
        for det in detections:
            x1, y1, x2, y2 = det.box

            file.write(
                f"{det.class_name} "
                f"{det.confidence:.4f} "
                f"{x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f}\n"
            )


def main():
    args = parse_args()

    weights_path = Path(args.weights)
    source_path = Path(args.source)

    if not weights_path.exists():
        raise FileNotFoundError(
            f"Could not find weights file:\n{weights_path}\n\n"
            "Check the exact training output folder."
        )

    if not source_path.exists():
        raise FileNotFoundError(
            f"Could not find source path:\n{source_path}\n\n"
            "Check that your test/images folder exists."
        )

    print()
    print("=" * 60)
    print("Azota YOLO Layout Detection Prediction")
    print("=" * 60)
    print(f"Weights:    {weights_path}")
    print(f"Source:     {source_path}")
    print(f"Confidence: {args.conf}")
    print(f"Image size: {args.imgsz}")
    print(f"Device:     {args.device}")
    print(f"Output name: {args.project}/{args.name}")    
    print("=" * 60)
    print()

    model = YOLO(str(weights_path))

    results = model.predict(
        source=str(source_path),
        conf=args.conf,
        imgsz=args.imgsz,
        device=args.device,
        project=args.project,
        name=args.name,
        save=True,
        save_txt=True,
        save_conf=True,
        exist_ok=True,
    )

    output_dir = Path(results[0].save_dir)
    cleaned_images_dir = output_dir / "cleaned_images"
    cleaned_labels_dir = output_dir / "cleaned_labels"

    cleaned_images_dir.mkdir(parents=True, exist_ok=True)
    cleaned_labels_dir.mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 60)
    print("Post-processing predictions")
    print("=" * 60)

    for result in results:
        image = result.orig_img
        image_height, image_width = image.shape[:2]

        raw_detections = yolo_result_to_detections(result)

        cleaned_detections = postprocess_detections(
            raw_detections,
            image_width=image_width,
            image_height=image_height,
        )

        image_path = Path(result.path)
        output_image_path = cleaned_images_dir / image_path.name
        output_txt_path = cleaned_labels_dir / f"{image_path.stem}.txt"

        cleaned_image = draw_detections(image, cleaned_detections)

        cv2.imwrite(str(output_image_path), cleaned_image)
        save_cleaned_txt(output_txt_path, cleaned_detections)

        print(
            f"{image_path.name}: "
            f"raw={len(raw_detections)} "
            f"cleaned={len(cleaned_detections)}"
        )

    print()
    print("=" * 60)
    print("Prediction finished")
    print("=" * 60)
    print(f"Raw YOLO results saved to:      {output_dir}")
    print(f"Cleaned images saved to:        {cleaned_images_dir}")
    print(f"Cleaned text labels saved to:   {cleaned_labels_dir}")
    print(f"Number of images processed:     {len(results)}")
    print()


if __name__ == "__main__":
    main()