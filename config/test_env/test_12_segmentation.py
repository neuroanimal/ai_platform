
import numpy as np
import torch
import cv2

from scipy import ndimage as ndi
from skimage import segmentation, color, measure
from skimage.draw import disk

import torchvision
from torchvision.models.segmentation import fcn_resnet50

print("=== VERSIONS ===")
print("OpenCV:", cv2.__version__)
print("PyTorch:", torch.__version__)
print("Torchvision:", torchvision.__version__)

print("\n=== SYNTHETIC IMAGE ===")

image = np.zeros((128, 128, 3), dtype=np.uint8)

rr, cc = disk((42, 42), 25, shape=image.shape[:2])
image[rr, cc] = (255, 0, 0)

rr, cc = disk((85, 85), 25, shape=image.shape[:2])
image[rr, cc] = (0, 255, 0)

image[20:50, 80:115] = (0, 0, 255)

assert image.shape == (128, 128, 3)

print("\n=== SLIC ===")

slic_labels = segmentation.slic(
    image,
    n_segments=8,
    compactness=10,
    start_label=1,
    channel_axis=-1,
)

slic_count = len(np.unique(slic_labels))

assert slic_labels.shape == (128, 128)
assert slic_count > 1

print("SLIC segments:", slic_count)

print("\n=== FELZENSZWALB ===")

felzenszwalb_labels = segmentation.felzenszwalb(
    image,
    scale=100,
    sigma=0.5,
    min_size=10,
    channel_axis=-1,
)

felzenszwalb_count = len(np.unique(felzenszwalb_labels))

assert felzenszwalb_labels.shape == (128, 128)
assert felzenszwalb_count > 1

print("Felzenszwalb segments:", felzenszwalb_count)

print("\n=== WATERSHED ===")

gray = color.rgb2gray(image)
mask = gray > 0

distance = ndi.distance_transform_edt(mask)

local_max = ndi.maximum_filter(distance, size=15) == distance
markers, marker_count = ndi.label(local_max & mask)

watershed_labels = segmentation.watershed(
    -distance,
    markers,
    mask=mask,
)

watershed_count = len(np.unique(watershed_labels)) - 1

assert watershed_labels.shape == (128, 128)
assert watershed_count > 0

print("Watershed regions:", watershed_count)

print("\n=== REGION ANALYSIS ===")

regions = measure.regionprops(watershed_labels)

for region in regions[:5]:
    print(
        "Label:", region.label,
        "Area:", region.area,
        "Centroid:", region.centroid,
        "BBox:", region.bbox,
    )

assert len(regions) > 0

print("\n=== OPENCV GRABCUT ===")

bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

mask_gc = np.zeros(image.shape[:2], dtype=np.uint8)

background_model = np.zeros((1, 65), dtype=np.float64)
foreground_model = np.zeros((1, 65), dtype=np.float64)

cv2.grabCut(
    bgr,
    mask_gc,
    (10, 10, 108, 108),
    background_model,
    foreground_model,
    2,
    cv2.GC_INIT_WITH_RECT,
)

grabcut_mask = np.isin(
    mask_gc,
    [cv2.GC_FGD, cv2.GC_PR_FGD],
)

assert grabcut_mask.shape == (128, 128)
assert grabcut_mask.any()

print("GrabCut foreground pixels:", int(grabcut_mask.sum()))

print("\n=== TORCHVISION FCN ===")

model = fcn_resnet50(
    weights=None,
    weights_backbone=None,
    num_classes=3,
)

model.eval()

input_tensor = torch.from_numpy(image.copy())
input_tensor = input_tensor.permute(2, 0, 1).float() / 255.0
input_tensor = input_tensor.unsqueeze(0)

with torch.inference_mode():
    output = model(input_tensor)

logits = output["out"]

assert logits.shape == (1, 3, 128, 128)
assert torch.isfinite(logits).all()

prediction = logits.argmax(dim=1)

assert prediction.shape == (1, 128, 128)

print("FCN logits:", tuple(logits.shape))
print("Segmentation mask:", tuple(prediction.shape))
print("Predicted classes:", torch.unique(prediction).tolist())

print("\nALL SEGMENTATION TESTS PASSED")

