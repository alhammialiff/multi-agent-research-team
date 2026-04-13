# Caco-2 Cell Permeability Prediction — TDC Caco2_Wang Report

## Contents Page
1. Introduction
2. Background: Caco-2 permeability and relevance
3. Dataset: TDC Caco2_Wang — retrieval and description
4. Modeling pipeline and reproducible code
   - 4.1 Data loading & splitting
   - 4.2 Featurization
   - 4.3 Models & training recipe
   - 4.4 Evaluation & reproducibility
5. Example use-cases
6. Results and explanation
7. Conclusion
8. Citations

## Introduction
This report investigates prediction of intestinal permeability as measured in Caco-2 cell assays using the Therapeutics Data Commons dataset TDC.Caco2_Wang. It provides: (a) biological and technical background; (b) instructions to retrieve and preprocess the dataset; (c) a fully reproducible modeling pipeline (featurization, models, training, evaluation) including runnable code snippets; (d) example use-cases; and (e) results interpretation and recommended next steps. Because this environment cannot execute code, the report includes exact commands and code to reproduce the experiments locally and expected benchmark results from TDC and literature (with IEEE citations). The Conclusion summarizes the key recommendations and invites further experimentation.

## Background: Caco-2 permeability and relevance
Caco-2 is a human intestinal epithelial cell line commonly used to estimate intestinal absorption and passive permeability of small molecules. Measured permeability values (often reported in cm/s and frequently log-transformed in some studies) are central to early ADME screening and help prioritize compounds with desirable oral bioavailability [1], [3].

Key points:
####
- Biological importance: Predicting Caco-2 permeability reduces expensive experimental screening and guides medicinal chemistry optimization.  
- Task formulation: Single-instance regression from SMILES to numeric permeability; TDC evaluates using scaffold splits and Mean Absolute Error (MAE) [2].  
- Practical note: Assay conditions and inter-lab variability can limit the lower bound for achievable predictive error; compare model MAE to assay noise.

## Dataset: TDC Caco2_Wang — retrieval and description
Dataset summary:
####
- Name: TDC.Caco2_Wang  
- Size: ~906 compounds  
- Label unit: permeability (cm/s)  
- Task: regression; recommended split: scaffold; official metric: MAE [2], [4].

Retrieve and inspect (recommended reproducible steps):

```bash
pip install pytdc rdkit-pypi scikit-learn xgboost numpy pandas
```

```python
from tdc.single_pred import ADME
data = ADME(name='Caco2_Wang')
df = data.get_data()         # DataFrame with 'Drug' (SMILES) and 'Y' (target)
splits = data.get_split(method='scaffold', seed=42)
train, valid, test = splits['train'], splits['valid'], splits['test']
```

Always inspect label distribution and missing values before modeling.

## Modeling pipeline and reproducible code
This section provides a practical pipeline that is easy to run and reproduce locally. Two featurization options are described: a fast baseline (fingerprints + descriptors) and a graph-based approach (stronger potential but heavier).

### 4.1 Data loading & splitting
####
- Use the scaffold split provided by PyTDC and keep the test set untouched until final evaluation.  
- Repeat experiments across multiple seeds (e.g., 3–5) and report mean ± std to assess variability.

### 4.2 Featurization
Option A — Fast baseline (recommended to start): RDKit Morgan fingerprint (ECFP4) + a small set of 2D descriptors.

```python
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors
import numpy as np

def featurize_smiles(smiles):
    mol = Chem.MolFromSmiles(smiles)
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
    arr = np.array(fp, dtype=int)
    desc = np.array([
        Descriptors.MolWt(mol),
        Descriptors.MolLogP(mol),
        Descriptors.TPSA(mol),
        Descriptors.NumHDonors(mol),
        Descriptors.NumHAcceptors(mol),
        Descriptors.NumRotatableBonds(mol)
    ], dtype=float)
    return np.concatenate([arr, desc])
```

Option B — Graph-based: use ChemProp, DGL-LifeSci, or PyTorch Geometric to build message-passing networks on atom/bond graphs. These often improve performance but require GPU and careful tuning.

### 4.3 Models & training recipe
Baseline models:
####
- XGBoost on concatenated fingerprint + descriptor vectors (strong, fast).  
- Alternatives: RandomForest, LightGBM, simple MLP.  
- Stronger: Ensemble of boosted trees and/or fine-tuned GNNs (ChemProp, Graphormer variants).

Example XGBoost training snippet:

```python
import xgboost as xgb
from sklearn.metrics import mean_absolute_error

# Build X_train, y_train, X_valid, y_valid, X_test, y_test using featurize_smiles

dtrain = xgb.DMatrix(X_train, label=y_train)
dvalid = xgb.DMatrix(X_valid, label=y_valid)
params = {'objective':'reg:squarederror','eta':0.05,'max_depth':6,'seed':42}
bst = xgb.train(params, dtrain, num_boost_round=2000, evals=[(dvalid,'eval')],
                early_stopping_rounds=50, verbose_eval=100)
y_pred = bst.predict(xgb.DMatrix(X_test))
mae = mean_absolute_error(y_test, y_pred)
print("Test MAE:", mae)
```

Hyperparameter suggestions:
####
- num_boost_round: 100–2000 with early stopping  
- learning_rate: 0.01–0.2  
- max_depth: 4–10  
- Use Optuna or randomized search over train+valid and report results on the held-out scaffold test.

### 4.4 Evaluation & reproducibility
####
- Primary metric: Mean Absolute Error (MAE) on the TDC scaffold test set.  
- Report mean ± std across seeds.  
- Save: model binary, predictions, split indices, random seeds, environment versions (PyTDC, RDKit, XGBoost).  

Reproducibility checklist: fix seeds, persist splits, log hyperparameters and training curves.

## Example use-cases
####
- Lead prioritization: Rank virtual libraries by predicted permeability and select top candidates for in vitro testing.  
- Medicinal chemistry: Support SAR decisions to increase permeability while balancing potency.  
- ADME cascade: Combine Caco-2 predictions with solubility, metabolic stability, and transporter liability models to filter candidates.

## Results and explanation
Transparency: this environment cannot run training or fetch live datasets. The results below summarize expected outcomes and interpretation grounded on TDC benchmark reports and literature.

Benchmark-informed expected outcomes:
####
- Competitive fingerprint+XGBoost pipeline (properly tuned) on the official scaffold split typically attains test MAE ≈ 0.27–0.35 (units: cm/s).  
- Top reported TDC entry (CaliciBoost) reports MAE ≈ 0.256; well-tuned XGBoost runs are around ≈ 0.274 on the same benchmark [2].  
- Simpler descriptor+ML baselines (untuned MLPs) can yield MAE > 0.35–0.40.

Interpretation guidance:
####
- MAE is in the same units as the labels; compare model MAE to assay reproducibility to judge practical utility.  
- If MAE is near leaderboard top (≈0.25–0.28), model is competitive; higher MAE (>0.4) indicates underfitting, poor featurization, or data leakage.  
- Gains usually come from richer featurization (learned graph embeddings), ensembling, and careful hyperparameter search with scaffold-aware validation.

How to obtain predictions locally:
####
- Run the retrieval + featurization + training code above in a Python environment with RDKit and PyTDC installed.  
- Save y_pred and compute MAE with sklearn.metrics.mean_absolute_error.  
- Repeat across multiple seeds and report mean ± std.

If you prefer, I can generate an executable Jupyter notebook implementing this pipeline (Colab-ready) or a Dockerfile for a reproducible compute environment.

## Conclusion
Caco-2 permeability prediction (TDC.Caco2_Wang) is a practical ADME regression task with direct relevance to oral drug discovery. A reproducible starting point is RDKit Morgan fingerprints combined with a small set of 2D descriptors trained with XGBoost; this approach is simple, fast, and often achieves competitive results on the TDC scaffold split (expected MAE ≈ 0.27–0.35). For higher performance, pursue ensembling, AutoML frameworks, or fine-tuned GNNs and ensure strict scaffold-aware validation and full reproducibility (split indices, seeds, environment). Running the provided notebook locally will produce actual predictions and allow benchmarking versus the TDC leaderboard [2].

## Citations
[1] Y. Sambuy et al., "The Caco-2 cell line as a model of the intestinal barrier: influence of cell and culture-related factors on Caco-2 cell functional characteristics," Cell Biology and Toxicology, vol. 21, no. 1, pp. 1–26, 2005.

[2] Therapeutics Data Commons, "TDC.Caco2_Wang Leaderboard," TDC benchmark pages, accessed 2024. [Online]. Available: https://tdcommons.ai/benchmark/admet_group/01caco2/

[3] N. Wang, J. Dong, and Y.-H. Deng, "ADME properties evaluation in drug discovery: prediction of Caco-2 cell permeability using a combination of NSGA-II and boosting," Journal of Chemical Information and Modeling, vol. 56, no. 4, pp. 763–773, 2016.

[4] K. Huang et al., "Therapeutics Data Commons: machine learning datasets and tasks for drug discovery and development," arXiv:2102.09548, 2021.
