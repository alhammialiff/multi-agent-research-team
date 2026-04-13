# Research Report: Caco-2 Cell Permeability — TDC Caco2_Wang Dataset & Machine Learning Predictions

## Contents Page
1. Introduction  
2. Background: Caco-2 permeability and relevance  
3. Dataset: TDC Caco2_Wang (retrieval & properties)  
4. Methods: reproducible ML pipeline  
   4.1 Data retrieval code  
   4.2 Featurization & preprocessing  
   4.3 Models & training protocol  
   4.4 Evaluation protocol & metrics  
5. Results (leaderboard summary, expected outcomes, reproduction instructions)  
6. Example use-cases  
7. Conclusion & next steps  
8. Citations

## Introduction
This report investigates Caco-2 cell effective permeability, retrieves metadata for the Therapeutics Data Commons (TDC) Caco2_Wang dataset, and presents a reproducible machine-learning pipeline to predict permeability from SMILES. Sections summarize biological background, dataset properties and recommended splits, featurization and modeling choices (with runnable code snippets), evaluation protocol aligned to TDC benchmarks, expected outcomes from leaderboard references, and practical use-cases. The conclusion outlines recommended next steps and reproducibility artifacts.

## Background: Caco-2 permeability and relevance
Caco-2 cells (human colon carcinoma line) are a widely used in vitro model of intestinal epithelial absorption. Measured effective permeability (commonly reported in cm/s) approximates oral absorption potential and is a standard ADME (absorption, distribution, metabolism, excretion) endpoint used during lead optimization. Key molecular determinants include molecular size, lipophilicity (LogP), topological polar surface area (TPSA), and hydrogen-bonding capacity; transporter and efflux mechanisms also influence measured values. Accurate in silico predictors accelerate screening and reduce assay burden [1], [2].

## Dataset: TDC Caco2_Wang (retrieval & properties)
- Source: Therapeutics Data Commons (TDC), dataset name: Caco2_Wang [1], [2].  
- Size: ~906 compounds with SMILES and measured Caco-2 effective permeability (cm/s).  
- Task: regression (continuous target Y = permeability).  
- Recommended split: scaffold split (provided by TDC) to assess scaffold-level generalization.  
- Primary evaluation: Mean Absolute Error (MAE) on the scaffold test split (lower is better).  
- Leaderboard context: published TDC leaderboard reports top entries near MAE ≈ 0.256 cm/s and many strong models in ~0.27–0.35; simple baselines often perform worse (~0.32–0.40) [2].

## Methods: reproducible ML pipeline
This section presents a runnable pipeline: data retrieval, featurization, modeling and evaluation. All code is Python-based and uses TDC and RDKit tooling.

### 4.1 Data retrieval code
#### Requirements
- Python 3.8+  
- pip install tdc rdkit-pypi scikit-learn xgboost pandas numpy joblib

#### Minimal retrieval snippet
```python
from tdc.single_pred import ADME
data = ADME(name='Caco2_Wang')
df = data.get_data()       # columns: 'Drug','SMILES','Y'
split = data.get_split()   # dict with 'train','valid','test'
train = df.loc[split['train']].reset_index(drop=True)
valid = df.loc[split['valid']].reset_index(drop=True)
test  = df.loc[split['test']].reset_index(drop=True)
```
Use the TDC benchmark_group wrapper to follow the exact train/validation/test configuration and evaluation formatting if needed [2].

### 4.2 Featurization & preprocessing
Two practical approaches:

#### A. RDKit 2D descriptors + Morgan fingerprints (fast, strong baseline)
- Morgan fingerprint: radius=2, nBits=2048  
- Descriptors: MolWt, MolLogP, TPSA, NumHDonors, NumHAcceptors

Featurizer snippet:
```python
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors
import numpy as np

def featurize(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
    arr = np.array(fp, dtype=int)
    desc = np.array([
        Descriptors.MolWt(mol),
        Descriptors.MolLogP(mol),
        Descriptors.TPSA(mol),
        Descriptors.NumHDonors(mol),
        Descriptors.NumHAcceptors(mol)
    ], dtype=float)
    return np.concatenate([arr, desc])
```

#### B. Graph-based representations
- D-MPNN / ChemProp or GNNs (PyG / DGL) provide learned structure-aware embeddings; they often improve performance but require more compute and careful tuning.

Preprocessing recommendations:
- Remove or flag invalid SMILES.  
- Standardize units (TDC reports cm/s).  
- Scale continuous descriptors (StandardScaler).  
- Use scaffold split and multiple seeds to estimate variability.

### 4.3 Models & training protocol
Recommended progression:
1. Trivial baseline: predict training mean.  
2. Tabular strong baseline: XGBoost on RDKit features + fingerprint.  
3. Neural baseline: MLP on descriptors+fingerprint.  
4. Advanced: GNNs (ChemProp / D-MPNN) and ensembling.

XGBoost example:
```python
import xgboost as xgb
dtrain = xgb.DMatrix(X_train, label=y_train)
dvalid = xgb.DMatrix(X_valid, label=y_valid)
params = {'objective':'reg:squarederror', 'eta':0.05, 'max_depth':6}
model = xgb.train(params, dtrain, num_boost_round=2000,
                  evals=[(dvalid,'valid')], early_stopping_rounds=50)
y_pred = model.predict(xgb.DMatrix(X_test))
```
Train with early stopping on the provided validation split; repeat across multiple random seeds (e.g., 3–5) and report mean±std MAE to align with TDC reporting.

### 4.4 Evaluation protocol & metrics
#### Metrics
- Primary: MAE (cm/s) on the scaffold test split.  
- Secondary: RMSE, R², Pearson correlation.

#### Evaluation snippet
```python
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
mae = mean_absolute_error(y_test, y_pred)
rmse = mean_squared_error(y_test, y_pred, squared=False)
r2 = r2_score(y_test, y_pred)
```
When using the TDC benchmark_group API, use group.evaluate(predictions) for consistent leaderboard-format evaluation.

## Results
Because execution of code and model training was not performed in this environment, the following summarizes dataset properties, TDC-reported leaderboard results, and expected outcomes when running the provided pipeline locally.

#### Leaderboard summary (TDC references)
- Top reported MAE: ≈0.256 cm/s (state-of-the-art ensemble entry).  
- Competitive XGBoost/ensemble results: ≈0.27–0.30 MAE.  
- Simple RDKit2D+MLP baselines: often ≈0.32–0.40 MAE [2].

#### Expected behavior when running the pipeline locally
- Mean predictor: large MAE (baseline).  
- XGBoost on RDKit features: strong baseline, typical MAE ≈0.27–0.30 with tuning and scaffold split.  
- GNN/ensembles: can approach reported SOTA ≈0.256 MAE but require careful model selection and ensembling.

#### Reproducibility instructions
1. Run data retrieval (Section 4.1) to obtain TDC splits.  
2. Featurize and cache feature arrays (Section 4.2).  
3. Train XGBoost with early stopping on validation; repeat across seeds.  
4. Evaluate on test split and report MAE±std; use TDC benchmark_group evaluate for standardized reporting.

## Example use-cases
#### Use-cases
- Virtual screening: rank candidates by predicted Caco-2 permeability to prioritize synthesis and testing.  
- Lead optimization: evaluate structural modifications in silico for permeability improvement.  
- Multi-parameter optimization: combine permeability predictions with potency, toxicity and solubility models.  
- Early ADME profiling: focus assays on promising candidates and reduce experimental burden.

## Conclusion & next steps
This report documents a reproducible pipeline to model Caco-2 permeability using the TDC Caco2_Wang dataset: data retrieval (TDC API), featurization (RDKit fingerprints and descriptors or graph-based embeddings), modeling (XGBoost baseline, MLP, GNN) and evaluation (MAE on scaffold test split). I was unable to execute model training in this environment; the included code and instructions enable you to reproduce benchmarks locally or on cloud compute. Recommended next steps:

#### Recommended next steps
- Run the pipeline locally (or on cloud) and report MAE±std across multiple seeds.  
- Start with XGBoost + RDKit features; then explore D-MPNN/ChemProp and ensembling for potential gains.  
- Use SHAP or feature-importance analysis to interpret drivers of predicted permeability.  
- If desired, request a Docker/Conda environment and a ready-to-run Jupyter notebook; I can prepare these artifacts or run experiments if a remote runtime is provided.

## Citations
[1] TDC, "ADME — Caco-2 (Cell Effective Permeability), Wang et al.," Therapeutics Data Commons. Available: https://tdcommons.ai/single_pred_tasks/adme/ (accessed 2026).  
[2] TDC, "TDC Caco2_Wang Leaderboard," Therapeutics Data Commons. Available: https://tdcommons.ai/benchmark/admet_group/01caco2/ (accessed 2026).  
[3] RDKit: Open-source cheminformatics; https://www.rdkit.org/ (accessed 2026).  
[4] XGBoost documentation, https://xgboost.readthedocs.io/ (accessed 2026).
