# ai/layout_detection/train_yolo_layout.py

"""
Train a YOLO object detection model for Azota exam layout detection.

Example from PowerShell, from the project root:

python ai/layout_detection/train_yolo_layout.py --data data/roboflow/azota-layout-v1/data.yaml --model yolov8s.pt --imgsz 1024 --epochs 5 --batch 4 --device 0 --name test_run_5_epochs

Real training example:

python ai/layout_detection/train_yolo_layout.py --data data/roboflow/azota-layout-v1/data.yaml --model yolov8s.pt --imgsz 1024 --epochs 200 --batch 4 --device 0 --name yolov8s_layout_v1
"""

from pathlib import Path
import argparse
import sys

import torch
from ultralytics import YOLO


def parse_args():
    parser = argparse.ArgumentParser(
        description="Train YOLO for Azota exam layout detection."
    )

    parser.add_argument(
        "--data",
        type=str,
        required=True,
        help="Path to the YOLO/Roboflow data.yaml file.",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="yolov8s.pt",
        help="YOLO model checkpoint, for example yolov8n.pt, yolov8s.pt, or yolov8m.pt.",
    )

    parser.add_argument(
        "--imgsz",
        type=int,
        default=1024,
        help="Image size for training. 1024 is recommended for document layouts if memory allows.",
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=100,
        help="Number of training epochs.",
    )

    parser.add_argument(
        "--batch",
        type=int,
        default=4,
        help="Batch size. Reduce if CUDA runs out of memory.",
    )

    parser.add_argument(
        "--device",
        type=str,
        default="0",
        help="Training device. Use 0 for first GPU, cpu for CPU.",
    )

    parser.add_argument(
        "--project",
        type=str,
        default="runs/azota_layout",
        help="Folder where training outputs will be saved.",
    )

    parser.add_argument(
        "--name",
        type=str,
        default="yolov8s_layout_v1",
        help="Name of this training run.",
    )

    parser.add_argument(
        "--patience",
        type=int,
        default=25,
        help="Early stopping patience. Training stops if validation does not improve.",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of dataloader workers.",
    )

    return parser.parse_args()


def print_training_summary(args):
    print()
    print("=" * 60)
    print("Azota YOLO Layout Detection Training")
    print("=" * 60)
    print(f"Dataset YAML: {args.data}")
    print(f"Model:        {args.model}")
    print(f"Image size:   {args.imgsz}")
    print(f"Epochs:       {args.epochs}")
    print(f"Batch size:   {args.batch}")
    print(f"Device:       {args.device}")
    print(f"Output:       {args.project}/{args.name}")
    print(f"Patience:     {args.patience}")
    print("=" * 60)
    print()

    print("PyTorch / CUDA check")
    print("--------------------")
    print(f"Torch version:      {torch.__version__}")
    print(f"CUDA build:         {torch.version.cuda}")
    print(f"CUDA available:     {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"GPU name:           {torch.cuda.get_device_name(0)}")
    else:
        print("GPU name:           No GPU detected by PyTorch")

    print()


def validate_paths(args):
    data_yaml = Path(args.data)

    if not data_yaml.exists():
        raise FileNotFoundError(
            f"Could not find data.yaml here:\n{data_yaml}\n\n"
            "Check that your Roboflow dataset is extracted in the expected folder."
        )

    if data_yaml.suffix.lower() not in [".yaml", ".yml"]:
        raise ValueError(
            f"The --data file should be a .yaml file, but got: {data_yaml}"
        )


def train_model(args):
    model = YOLO(args.model)

    results = model.train(
        data=args.data,
        imgsz=args.imgsz,
        epochs=args.epochs,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        patience=args.patience,
        workers=args.workers,
        plots=True,
        cache=False,
    )

    return results


def main():
    args = parse_args()

    try:
        validate_paths(args)
        print_training_summary(args)

        if args.device != "cpu" and not torch.cuda.is_available():
            print(
                "WARNING: You selected a GPU device, but PyTorch says CUDA is not available."
            )
            print(
                "Training may fail. Use --device cpu or fix CUDA/PyTorch installation."
            )
            print()

        train_model(args)

        best_weights = Path(args.project) / args.name / "weights" / "best.pt"
        last_weights = Path(args.project) / args.name / "weights" / "last.pt"

        print()
        print("=" * 60)
        print("Training finished")
        print("=" * 60)

        if best_weights.exists():
            print(f"Best weights: {best_weights}")
        else:
            print(f"Best weights expected at: {best_weights}")

        if last_weights.exists():
            print(f"Last weights: {last_weights}")

        print()
        print("Next step: run prediction on test images, for example:")
        print(
            f"python ai/layout_detection/predict_yolo_layout.py "
            f"--weights {best_weights} "
            f"--source data/roboflow/azota-layout-v1/test/images "
            f"--conf 0.25 "
            f"--imgsz {args.imgsz} "
            f"--name test_predictions_v1"
        )

    except RuntimeError as error:
        message = str(error).lower()

        print()
        print("=" * 60)
        print("Training failed")
        print("=" * 60)
        print(error)
        print()

        if "out of memory" in message or "cuda" in message:
            print("This looks like a CUDA/GPU memory issue.")
            print("Try one of these:")
            print("  1. Lower batch size: --batch 2")
            print("  2. Lower image size: --imgsz 768")
            print("  3. Use smaller model: --model yolov8n.pt")
            print()
            print("Example:")
            print(
                "python ai/layout_detection/train_yolo_layout.py "
                "--data data/roboflow/azota-layout-v1/data.yaml "
                "--model yolov8s.pt "
                "--imgsz 768 "
                "--epochs 100 "
                "--batch 2 "
                "--device 0 "
                "--name yolov8s_layout_v1_low_memory"
            )

        sys.exit(1)

    except Exception as error:
        print()
        print("=" * 60)
        print("Training failed")
        print("=" * 60)
        print(error)
        sys.exit(1)


if __name__ == "__main__":
    main()