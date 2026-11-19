
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchaudio

from sklearn.datasets import make_moons, load_iris
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier
from statsmodels.tsa.ar_model import AutoReg
import sympy as sp

torch.manual_seed(42)
np.random.seed(42)

print("=== PYTORCH ===")
X = torch.randn(100, 4)
y = (X[:, 0] + X[:, 1] > 0).float().unsqueeze(1)

model = nn.Sequential(
    nn.Linear(4, 16),
    nn.ReLU(),
    nn.Linear(16, 1),
    nn.Sigmoid()
)

optimizer = optim.Adam(model.parameters(), lr=0.01)
loss_fn = nn.BCELoss()

for epoch in range(100):
    optimizer.zero_grad()
    prediction = model(X)
    loss = loss_fn(prediction, y)
    loss.backward()
    optimizer.step()

print("Loss:", round(loss.item(), 5))
print("Prediction:", model(X[:3]).detach().flatten().tolist())

assert loss.item() < 0.3

print("\n=== TORCHVISION ===")
from torchvision.models import resnet18

vision_model = resnet18(weights=None).eval()
image = torch.randn(1, 3, 224, 224)

with torch.no_grad():
    output = vision_model(image)

print("ResNet output shape:", tuple(output.shape))
assert output.shape == (1, 1000)

print("\n=== TORCHAUDIO ===")
waveform = torch.randn(1, 16000)
spectrogram = torchaudio.transforms.MelSpectrogram(
    sample_rate=16000,
    n_mels=40
)(waveform)

print("Mel spectrogram:", tuple(spectrogram.shape))
assert spectrogram.shape[1] == 40

print("\n=== SCIKIT-LEARN ===")
X, y = make_moons(n_samples=500, noise=0.2, random_state=42)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42
)

lr = make_pipeline(
    StandardScaler(),
    LogisticRegression()
)
lr.fit(X_train, y_train)

rf = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)
rf.fit(X_train, y_train)

print("Logistic regression:", accuracy_score(y_test, lr.predict(X_test)))
print("Random forest:", accuracy_score(y_test, rf.predict(X_test)))

assert accuracy_score(y_test, rf.predict(X_test)) > 0.85

print("\n=== XGBOOST ===")
xgb = XGBClassifier(
    n_estimators=50,
    max_depth=3,
    learning_rate=0.1,
    eval_metric="logloss",
    n_jobs=2
)
xgb.fit(X_train, y_train)

score = accuracy_score(y_test, xgb.predict(X_test))
print("XGBoost accuracy:", score)
assert score > 0.85

print("\n=== STATSMODELS ===")
series = np.sin(np.arange(100) * 0.1) + np.random.normal(0, 0.1, 100)
ar = AutoReg(series, lags=5).fit()

print("AR forecast:", ar.predict(start=100, end=104))

print("\n=== SYMPY ===")
x = sp.Symbol("x")
equation = sp.solve(x**2 - 5*x + 6, x)

print("Equation roots:", equation)
assert equation == [2, 3]

print("\nALL ML/DL TESTS PASSED")

