import transformers

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



print("\n=== FLAIR ===")

import torch
import flair
import transformers
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
    print(
        f"Sentence {i}: shape={tuple(vector.shape)}, "
        f"finite={torch.isfinite(vector).all().item()}, "
        f"norm={vector.norm().item():.6f}"
    )

    assert vector.numel() == embeddings.embedding_length
    assert torch.isfinite(vector).all()
    assert vector.norm().item() > 0

assert len(vectors) == 2

print("FLAIR DOCUMENT EMBEDDING TEST PASSED")


# print("\n=== FLAIR ===")
# from flair.data import Sentence

# sentence = Sentence("This is a test sentence.")
# print(sentence.to_tokenized_string())
# assert len(sentence) > 0


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
print("Frequency of 'kot':", wordfreq.zipf_frequency("kot", "pl"))

print("\n=== LEMMINFLECT ===")
print("Inflections:", lemminflect.getLemma("cats", upos="NOUN"))

print("\n=== TEXTACY ===")
print("Textacy version:", textacy.__version__)

print("\n=== FTfy ===")
print(ftfy.fix_text("FranÃ§ais"))

print("\n=== REGEX ===")
print(regex.findall(r"\p{L}+", "Zażółć gęślą jaźń 123"))

print("\nALL NLP TESTS PASSED")

