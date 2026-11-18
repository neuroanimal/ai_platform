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
from flair.data import Sentence

sentence = Sentence("This is a test sentence.")
print(sentence.to_tokenized_string())
assert len(sentence) > 0

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

