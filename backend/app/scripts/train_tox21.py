"""
Phase 2 — Train Tox21 MultitaskClassifier and save checkpoint.

Run from project root:
    python backend/app/scripts/train_tox21.py

The checkpoint is saved to backend/app/data/models/tox21_attentivefp/
and will be picked up automatically by deepchem_service.py on next restart.

Expected training time: ~5 min on CPU, ~1 min on GPU.
Expected ROC-AUC: 0.75–0.82 on validation set.
"""

import os
import sys
import numpy as np

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

CHECKPOINT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "data", "models", "tox21_attentivefp"
)
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

print("Loading DeepChem + Tox21 dataset...")
import deepchem as dc

tasks, datasets, transformers = dc.molnet.load_tox21(
    featurizer="ECFP", splitter="random"
)
train, valid, test = datasets
print(f"Tasks: {tasks}")
print(f"Train: {len(train)}  Valid: {len(valid)}  Test: {len(test)}")

print("\nTraining MultitaskClassifier (20 epochs)...")
model = dc.models.MultitaskClassifier(
    n_tasks=len(tasks),
    n_features=1024,
    layer_sizes=[1024, 512, 256],
    dropouts=0.3,
    batch_size=64,
    learning_rate=0.001,
    model_dir=CHECKPOINT_DIR,
)

losses = model.fit(train, nb_epoch=20, deterministic=False)

print("\nEvaluating...")
metric = dc.metrics.Metric(dc.metrics.roc_auc_score, np.mean)
train_score = model.evaluate(train, [metric], transformers)
valid_score = model.evaluate(valid, [metric], transformers)
print(f"Train ROC-AUC: {train_score}")
print(f"Valid ROC-AUC: {valid_score}")

model.save_checkpoint()
print(f"\nCheckpoint saved to: {CHECKPOINT_DIR}")
print("Restart the FastAPI server — deepchem_service.py will load it automatically.")