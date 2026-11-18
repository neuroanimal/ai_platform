
import transformers

# Compatibility: Flair 0.15.1 with Transformers 5.x
transformers.LayoutLMv2FeatureExtractor = (
    transformers.LayoutLMv2ImageProcessor
)

import spacy
import nltk
import stanza
import flair
import gensim
import wordfreq
import lemminflect
import textacy
import ftfy
import regex
import torch

print("=== SPACY ===")
nlp = spacy.blank("pl")
doc = nlp("Ala ma kota. Kot mieszka w Krakowie.")

for token in doc:
    print(token.text, token.pos_, token.is_alpha)

assert len(doc) > 0

print("\n=== NLTK ===")
from nltk.tokenize import word_tokenize

text = "Natural language processing is interesting."
tokens = word_tokenize(text, preserve_line=True)
print(tokens)
assert len(tokens) > 0

print("\n=== STANZA ===")
from stanza.models.common.doc import Document

doc = Document([
    [{"text": "To"}, {"text": "jest"}, {"text": "test"}]
])
print("Stanza document:", doc)
assert len(doc.sentences) > 0

print("\n=== FLAIR ===")

from flair.data import Sentence
from flair.embeddings import TransformerDocumentEmbeddings

model_name = "hf-internal-testing/tiny-random-distilbert"

print("Flair:", flair.__version__)
print("Transformers:", transformers.__version__)
print("Model:", model_name)

embeddings = TransformerDocumentEmbeddings(
    model_name,
    fine_tune=False,
    needs_manual_ocr=False,
)

print("Embedding dimension:", embeddings.embedding_length)
print("Manual OCR:", embeddings.needs_manual_ocr)
print("Tokenizer OCR boxes:", embeddings.tokenizer_needs_ocr_boxes)
print("Feature extractor:", embeddings.feature_extractor)

assert not embeddings.needs_manual_ocr
assert not embeddings.tokenizer_needs_ocr_boxes
assert embeddings.embedding_length > 0

sentences = [
    Sentence("To jest pierwszy test modelu Flair."),
    Sentence("Transformers pięć współpracuje z biblioteką Flair."),
]

embeddings.embed(sentences)

vectors = [sentence.get_embedding() for sentence in sentences]

for i, vector in enumerate(vectors, start=1):
    finite = torch.isfinite(vector).all().item()
    norm = vector.norm().item()

    print(
        f"Sentence {i}: shape={tuple(vector.shape)}, "
        f"finite={finite}, norm={norm:.6f}"
    )

    assert vector.numel() == embeddings.embedding_length
    assert finite
    assert norm > 0

assert len(vectors) == 2

print("FLAIR DOCUMENT EMBEDDING TEST PASSED")

print("\n=== GENSIM ===")
from gensim.models import Word2Vec

sentences = [
    ["kot", "pies", "zwierzę"],
    ["pies", "zwierzę", "dom"],
    ["kot", "dom", "zwierzę"],
    ["język", "polski", "lingwistyka"]
]

model = Word2Vec(
    sentences,
    vector_size=20,
    window=2,
    min_count=1,
    workers=1,
    epochs=20
)

print("Similar words:", model.wv.most_similar("kot"))
assert model.wv["kot"].shape == (20,)

print("\n=== WORDFREQ ===")
frequency = wordfreq.zipf_frequency("kot", "pl")
print("Frequency of 'kot':", frequency)
assert frequency > 0

print("\n=== LEMMINFLECT ===")
inflections = lemminflect.getLemma("cats", upos="NOUN")
print("Inflections:", inflections)
assert inflections is not None

print("\n=== TEXTACY ===")
print("Textacy version:", textacy.__version__)

print("\n=== FTfy ===")
fixed = ftfy.fix_text("FranÃ§ais")
print(fixed)
assert fixed == "Français"

print("\n=== REGEX ===")
matches = regex.findall(r"\p{L}+", "Zażółć gęślą jaźń 123")
print(matches)
assert matches == ["Zażółć", "gęślą", "jaźń"]

print("\nALL NLP TESTS PASSED")

