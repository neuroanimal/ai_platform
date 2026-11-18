
import torch
import numpy as np
import transformers

from transformers import (
    CLIPConfig,
    CLIPTextConfig,
    CLIPVisionConfig,
    CLIPModel,
)

print("=== VERSIONS ===")
print("PyTorch:", torch.__version__)
print("Transformers:", transformers.__version__)

torch.manual_seed(42)

print("\n=== CLIP CONFIGURATION ===")

text_config = CLIPTextConfig(
    vocab_size=1000,
    hidden_size=64,
    intermediate_size=128,
    num_hidden_layers=2,
    num_attention_heads=4,
    max_position_embeddings=32,
    projection_dim=32,
)

vision_config = CLIPVisionConfig(
    hidden_size=64,
    intermediate_size=128,
    num_hidden_layers=2,
    num_attention_heads=4,
    image_size=32,
    patch_size=8,
    num_channels=3,
)

config = CLIPConfig(
    text_config=text_config.to_dict(),
    vision_config=vision_config.to_dict(),
    projection_dim=32,
)

model = CLIPModel(config)
model.eval()

print("Parameters:", sum(p.numel() for p in model.parameters()))
print("Projection dimension:", config.projection_dim)

print("\n=== IMAGE INPUT ===")

pixel_values = torch.rand(2, 3, 32, 32)

assert pixel_values.shape == (2, 3, 32, 32)

print("Images:", tuple(pixel_values.shape))

print("\n=== TEXT INPUT ===")

input_ids = torch.randint(0, 1000, (2, 16))
attention_mask = torch.ones_like(input_ids)

assert input_ids.shape == (2, 16)

print("Token IDs:", tuple(input_ids.shape))

print("\n=== MULTIMODAL INFERENCE ===")

with torch.inference_mode():
    outputs = model(
        input_ids=input_ids,
        attention_mask=attention_mask,
        pixel_values=pixel_values,
        return_loss=True,
    )

image_embeddings = outputs.image_embeds
text_embeddings = outputs.text_embeds
logits_per_image = outputs.logits_per_image

assert image_embeddings.shape == (2, 32)
assert text_embeddings.shape == (2, 32)
assert logits_per_image.shape == (2, 2)

assert torch.isfinite(image_embeddings).all()
assert torch.isfinite(text_embeddings).all()
assert torch.isfinite(logits_per_image).all()

print("Image embeddings:", tuple(image_embeddings.shape))
print("Text embeddings:", tuple(text_embeddings.shape))
print("Similarity logits:", tuple(logits_per_image.shape))

print("\n=== CROSS-MODAL SIMILARITY ===")

image_normalized = torch.nn.functional.normalize(
    image_embeddings,
    dim=-1,
)

text_normalized = torch.nn.functional.normalize(
    text_embeddings,
    dim=-1,
)

similarity = image_normalized @ text_normalized.T

assert similarity.shape == (2, 2)
assert torch.isfinite(similarity).all()

print("Similarity matrix:")
print(similarity)

print("\n=== IMAGE / TEXT ENCODERS ===")

with torch.inference_mode():
    image_features = model.get_image_features(
        pixel_values=pixel_values
    )

    text_features = model.get_text_features(
        input_ids=input_ids,
        # attention_mask=attention_mask,
    )


if hasattr(image_features, "pooler_output"):
    image_features = image_features.pooler_output
elif hasattr(image_features, "last_hidden_state"):
    image_features = image_features.last_hidden_state[:, 0, :]

if hasattr(text_features, "pooler_output"):
    text_features = text_features.pooler_output
elif hasattr(text_features, "last_hidden_state"):
    text_features = text_features.last_hidden_state[:, 0, :]


assert image_features.shape == (2, 32)
assert text_features.shape == (2, 32)

print("Image encoder:", tuple(image_features.shape))
print("Text encoder:", tuple(text_features.shape))

print("\n=== MULTIMODAL LOSS ===")

loss = outputs.loss

assert loss is not None
assert torch.isfinite(loss)

print("Contrastive loss:", float(loss))

print("\nALL MULTIMODAL TESTS PASSED")

