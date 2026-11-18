
import tempfile
from pathlib import Path
import numpy as np

print("\n=== OPTUNA ===")
import optuna

def objective(trial):
    x = trial.suggest_float("x", -10, 10)
    y = trial.suggest_float("y", -10, 10)
    return x * x + y * y

study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=40)

print("Optuna best:", study.best_value, study.best_params)
assert study.best_value < 2.0

print("\n=== MLFLOW ===")
import mlflow

with tempfile.TemporaryDirectory() as tmp:
    mlflow.set_tracking_uri(Path(tmp).as_uri())
    mlflow.set_experiment("local-test")

    with mlflow.start_run() as run:
        mlflow.log_param("model", "test-model")
        mlflow.log_param("features", 4)
        mlflow.log_metric("accuracy", 0.95)
        run_id = run.info.run_id

    loaded_run = mlflow.get_run(run_id)
    print("MLflow:", loaded_run.data.params, loaded_run.data.metrics)
    assert loaded_run.data.metrics["accuracy"] == 0.95

print("\n=== TENSORBOARD ===")
from torch.utils.tensorboard import SummaryWriter

with tempfile.TemporaryDirectory() as tmp:
    writer = SummaryWriter(log_dir=tmp)
    writer.add_scalar("training/loss", 0.25, 1)
    writer.add_scalar("training/accuracy", 0.95, 1)
    writer.flush()
    writer.close()

    event_files = list(Path(tmp).glob("events.out.tfevents.*"))
    print("TensorBoard event files:", len(event_files))
    assert event_files

print("\n=== JOBLIB ===")
import joblib

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "array.joblib"
    original = np.array([[1, 2], [3, 4]], dtype=np.float32)
    joblib.dump(original, path)
    restored = joblib.load(path)
    print("Joblib restored:", restored.tolist())
    assert np.array_equal(original, restored)

print("\n=== SHAP ===")
import shap
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier

iris = load_iris()
X, y = iris.data, iris.target

model = RandomForestClassifier(n_estimators=20, random_state=42)
model.fit(X, y)

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X[:3])

print("SHAP output type:", type(shap_values).__name__)
print("SHAP explanation computed")
assert shap_values is not None

print("\n=== LIME ===")
from lime.lime_tabular import LimeTabularExplainer

lime_explainer = LimeTabularExplainer(
    X,
    feature_names=iris.feature_names,
    class_names=iris.target_names.tolist(),
    mode="classification",
    discretize_continuous=True,
    random_state=42,
)

explanation = lime_explainer.explain_instance(
    X[0],
    model.predict_proba,
    num_features=4,
    num_samples=500,
)
print("LIME explanation:", explanation.as_list())
assert len(explanation.as_list()) > 0

print("\n=== EVIDENTLY ===")
from evidently import Report
from evidently.presets import DataDriftPreset
import pandas as pd

rng = np.random.default_rng(42)

reference = pd.DataFrame({
    "age": rng.normal(35, 8, 300),
    "income": rng.normal(5000, 1000, 300),
})

current = pd.DataFrame({
    "age": rng.normal(42, 10, 300),
    "income": rng.normal(6500, 1300, 300),
})

report = Report([DataDriftPreset()])
snapshot = report.run(
    reference_data=reference,
    current_data=current,
)
print("Evidently report:", type(snapshot).__name__)
assert snapshot is not None

print("\n=== TORCHMETRICS ===")
import torch
from torchmetrics.classification import MulticlassAccuracy

metric = MulticlassAccuracy(num_classes=3)
predictions = torch.tensor([
    [0.9, 0.1, 0.0],
    [0.1, 0.8, 0.1],
    [0.1, 0.2, 0.7],
    [0.8, 0.1, 0.1],
])
targets = torch.tensor([0, 1, 2, 1])

metric.update(predictions, targets)
accuracy = metric.compute().item()
print("TorchMetrics accuracy:", accuracy)
assert abs(accuracy - 0.75) < 1e-6

print("\n=== LIGHTNING ===")
import lightning.pytorch as pl
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

class TinyClassifier(pl.LightningModule):
    def __init__(self):
        super().__init__()
        self.layer = nn.Linear(4, 3)
        self.loss_fn = nn.CrossEntropyLoss()

    def forward(self, x):
        return self.layer(x)

    def training_step(self, batch, batch_idx):
        x, y = batch
        loss = self.loss_fn(self(x), y)
        self.log("train_loss", loss)
        return loss

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=0.01)

dataset = TensorDataset(
    torch.randn(32, 4),
    torch.randint(0, 3, (32,)),
)
loader = DataLoader(dataset, batch_size=8)

trainer = pl.Trainer(
    max_epochs=1,
    accelerator="cpu",
    devices=1,
    logger=False,
    enable_checkpointing=False,
    enable_model_summary=False,
    enable_progress_bar=False,
    limit_train_batches=2,
    enable_validation=False,
)

trainer.fit(TinyClassifier(), train_dataloaders=loader)
print("Lightning training completed")

print("\nALL TESTS PASSED")

