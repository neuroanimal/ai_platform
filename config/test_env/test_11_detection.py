
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
import torchvision
from torchvision.ops import box_iou, nms

import ultralytics
from ultralytics import YOLO

print("=== VERSIONS ===")
print("PyTorch:", torch.__version__)
print("Torchvision:", torchvision.__version__)
print("Ultralytics:", ultralytics.__version__)

print("\n=== SYNTHETIC IMAGE ===")

image = np.zeros((256, 256, 3), dtype=np.uint8)
image[40:120, 40:120] = (255, 0, 0)
image[140:220, 140:220] = (0, 255, 0)

assert image.shape == (256, 256, 3)

print("\n=== BOUNDING BOXES ===")

boxes = torch.tensor([
    [10.0, 10.0, 100.0, 100.0],
    [20.0, 20.0, 110.0, 110.0],
    [150.0, 150.0, 220.0, 220.0],
])

scores = torch.tensor([0.95, 0.80, 0.90])

iou = box_iou(boxes, boxes)
keep = nms(boxes, scores, iou_threshold=0.5)

assert iou.shape == (3, 3)
assert torch.allclose(iou.diag(), torch.ones(3))
assert len(keep) == 2

print("IoU matrix:", iou)
print("NMS selected indices:", keep.tolist())

print("\n=== YOLO MODEL ===")

cfg = (
    Path(ultralytics.__file__).parent
    / "cfg"
    / "models"
    / "11"
    / "yolo11.yaml"
)

assert cfg.exists(), f"YOLO configuration not found: {cfg}"

model = YOLO(str(cfg), task="detect")

model.model.eval()

print("Model config:", cfg.name)
print("Model task:", model.task)
print("Parameters:", sum(p.numel() for p in model.model.parameters()))

print("\n=== YOLO INFERENCE ===")

results = model.predict(
    source=image,
    imgsz=256,
    device="cpu",
    verbose=False,
    save=False,
)

assert len(results) == 1

result = results[0]

assert result.orig_shape == (256, 256)
assert result.boxes is not None

print("Original image:", result.orig_shape)
print("Detections:", len(result.boxes))

if len(result.boxes) > 0:
    print("Boxes:", result.boxes.xyxy.shape)
    print("Scores:", result.boxes.conf.shape)
    print("Classes:", result.boxes.cls.shape)

print("YOLO INFERENCE TEST PASSED")

print("\n=== BYTETRACK API ===")

from ultralytics.trackers.byte_tracker import BYTETracker

tracker_args = SimpleNamespace(
    track_high_thresh=0.5,
    track_low_thresh=0.1,
    new_track_thresh=0.6,
    track_buffer=30,
    match_thresh=0.8,
    fuse_score=True,
    mot20=False,
)

tracker = BYTETracker(
    tracker_args,
    # frame_rate=30,
)

assert tracker is not None

print("ByteTrack initialized:", type(tracker).__name__)

print("\nALL OBJECT DETECTION TESTS PASSED")

