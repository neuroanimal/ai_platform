
import tempfile
from pathlib import Path

import numpy as np
import torch

print("=== VERSIONS ===")

import cv2
import PIL
import skimage
import torchvision
import kornia
import albumentations
import imageio
import ultralytics
import timm

print("OpenCV:", cv2.__version__)
print("Pillow:", PIL.__version__)
print("scikit-image:", skimage.__version__)
print("torch:", torch.__version__)
print("torchvision:", torchvision.__version__)
print("Kornia:", kornia.__version__)
print("Albumentations:", albumentations.__version__)
print("ImageIO:", imageio.__version__)
print("Ultralytics:", ultralytics.__version__)
print("timm:", timm.__version__)

print("\n=== TEST IMAGE ===")

image = np.zeros((256, 256, 3), dtype=np.uint8)
image[40:120, 40:120] = (255, 0, 0)
image[140:220, 140:220] = (0, 255, 0)
cv2.circle(image, (128, 128), 30, (0, 0, 255), -1)

assert image.shape == (256, 256, 3)
assert image.dtype == np.uint8
print("Image:", image.shape, image.dtype)

print("\n=== OPENCV ===")

gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
blur = cv2.GaussianBlur(gray, (5, 5), 0)
edges = cv2.Canny(blur, 50, 150)

kernel = np.ones((3, 3), np.uint8)
morph = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

contours, _ = cv2.findContours(
    morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
)

assert gray.shape == (256, 256)
assert blur.shape == gray.shape
assert edges.shape == gray.shape
assert len(contours) > 0

matrix = cv2.getPerspectiveTransform(
    np.float32([[0, 0], [255, 0], [255, 255], [0, 255]]),
    np.float32([[10, 10], [245, 0], [255, 245], [0, 255]])
)

warped = cv2.warpPerspective(image, matrix, (256, 256))
assert warped.shape == image.shape

print("Contours:", len(contours))
print("Perspective transform: PASSED")

print("\n=== PILLOW ===")

from PIL import Image, ImageFilter

pil_image = Image.fromarray(image)
pil_gray = pil_image.convert("L")
pil_blur = pil_gray.filter(ImageFilter.GaussianBlur(radius=2))

assert pil_image.size == (256, 256)
assert pil_blur.mode == "L"

print("Pillow modes:", pil_image.mode, pil_gray.mode)

print("\n=== IMAGEIO ===")

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "vision_test.png"
    imageio.imwrite(path, image)
    loaded = imageio.imread(path)

    assert loaded.shape == image.shape
    assert np.array_equal(loaded, image)

print("ImageIO read/write: PASSED")

print("\n=== SCIKIT-IMAGE ===")

from skimage import color, filters, morphology, measure, transform

sk_gray = color.rgb2gray(image)
threshold = filters.threshold_otsu(sk_gray)
binary = sk_gray > threshold
cleaned = morphology.remove_small_objects(binary, min_size=10)
labels = measure.label(cleaned)
regions = measure.regionprops(labels)
resized = transform.resize(image, (128, 128), anti_aliasing=True)

assert sk_gray.shape == (256, 256)
assert cleaned.shape == binary.shape
assert resized.shape == (128, 128, 3)

print("Regions:", len(regions))
print("Resized:", resized.shape)

print("\n=== TORCHVISION ===")

from torchvision.transforms import functional as TF
from torchvision.transforms import InterpolationMode

tensor = TF.to_tensor(image)
resized_tensor = TF.resize(
    tensor,
    [128, 128],
    interpolation=InterpolationMode.BILINEAR
)

assert tensor.shape == (3, 256, 256)
assert resized_tensor.shape == (3, 128, 128)
assert torch.isfinite(resized_tensor).all()

print("Tensor:", tuple(tensor.shape))
print("Resized tensor:", tuple(resized_tensor.shape))

print("\n=== KORNIA ===")

import kornia.filters as KF
import kornia.geometry.transform as KT

batch = tensor.unsqueeze(0)
kornia_blur = KF.gaussian_blur2d(batch, (5, 5), (1.5, 1.5))
kornia_edges = KF.sobel(batch)
kornia_resized = KT.resize(batch, (128, 128))

assert kornia_blur.shape == batch.shape
assert kornia_edges.shape == (1, 3, 256, 256)
assert kornia_resized.shape == (1, 3, 128, 128)
assert torch.isfinite(kornia_edges).all()

print("Blur:", tuple(kornia_blur.shape))
print("Sobel:", tuple(kornia_edges.shape))

print("\n=== ALBUMENTATIONS ===")

import albumentations as A

augmentation = A.Compose([
    A.HorizontalFlip(p=1.0),
    A.RandomBrightnessContrast(p=1.0),
])

augmented = augmentation(image=image)["image"]

assert augmented.shape == image.shape
assert augmented.dtype == image.dtype

print("Augmented:", augmented.shape)




print("\n=== TIMM ===")

from timm.data import resolve_data_config
from timm.data.transforms_factory import create_transform

pretrained_cfg = {
    "input_size": (3, 224, 224),
    "mean": (0.485, 0.456, 0.406),
    "std": (0.229, 0.224, 0.225),
    "interpolation": "bicubic",
    "crop_pct": 0.875,
}

config = resolve_data_config(
    {},
    pretrained_cfg=pretrained_cfg,
)

transform = create_transform(
    **config,
    is_training=False,
)

transformed = transform(Image.fromarray(image))

assert transformed.shape == (3, 224, 224)
assert torch.isfinite(transformed).all()

print("Data config:", config)
print("Transform output:", tuple(transformed.shape))
print("TIMM TRANSFORM TEST PASSED")



print("\n=== ULTRALYTICS ===")

from ultralytics.utils import ops

boxes = torch.tensor([
    [10.0, 10.0, 100.0, 100.0],
    [20.0, 20.0, 120.0, 120.0],
])

xywh = ops.xyxy2xywh(boxes)
xyxy = ops.xywh2xyxy(xywh)

assert xywh.shape == (2, 4)
assert torch.allclose(xyxy, boxes)

print("Bounding box conversion: PASSED")

print("\nALL COMPUTER VISION TESTS PASSED")


