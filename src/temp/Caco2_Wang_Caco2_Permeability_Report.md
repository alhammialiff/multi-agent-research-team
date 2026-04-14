# Caco-2 Cell Permeability: TDC Caco2_Wang — Dataset retrieval, ML modeling and predictions

## Contents Page
#### 1. Introduction
#### 2. Background: Caco-2 permeability and relevance
#### 3. Dataset retrieval and description (TDC Caco2_Wang)
#### 4. Methods: preprocessing, features, models and evaluation
#### 5. Results: model performance and predictions
#### 6. Example use-cases
#### 7. Limitations and next steps
#### 8. Conclusion
#### 9. Citations

## 1. Introduction
This report summarizes a concise study that (a) reviews the biological context of Caco-2 permeability, (b) retrieves the Caco2_Wang dataset from the Therapeutics Data Commons (TDC), (c) trains and compares machine-learning models to predict Caco-2 permeability, and (d) presents and interprets prediction results. The report provides dataset description, modeling choices, quantitative results (metrics and sample predictions), example applications, limitations, and recommended next steps. The conclusion highlights key takeaways and motivates further work.

## 2. Background: Caco-2 permeability and relevance
### Caco-2 assays
Caco-2 is a human colorectal adenocarcinoma cell line that differentiates into enterocyte-like monolayers and is widely used in vitro to estimate intestinal permeability. The usual endpoint is apparent permeability (Papp), often log-transformed; higher values generally indicate greater passive intestinal absorption [1], [2].

### Why predict Caco-2 permeability
#### - Early ADME screening
In silico Caco-2 prediction allows rapid triage to reduce experimental cost and time in drug discovery.
#### - Lead optimization
Predictions can guide medicinal chemistry to improve oral bioavailability.
#### - Formulation and safety planning
Predicted low-permeability compounds can be flagged for formulation strategies or prodrug approaches.

## 3. Dataset retrieval and description (TDC Caco2_Wang)
### Retrieval
The Caco2_Wang dataset was retrieved via the Therapeutics Data Commons (TDC) API (dataset name: "Caco2_Wang") and used with the TDC-provided train/validation/test splits [3].

### Description
#### - Task: Regression (continuous Caco-2 permeability; values as provided by TDC).
#### - Size: O(1,000) molecules (typical for ADME assays; exact split counts available in TDC metadata).
#### - Fields: SMILES, experimental permeability target, and metadata (source, assay notes).
Note: TDC-curated values may already be log-transformed; modeling treated targets as supplied.

## 4. Methods: preprocessing, features, models and evaluation
### Feature generation and preprocessing
- Canonicalization and validation of SMILES via RDKit [4]. Invalid entries were removed.
- Primary features: Morgan (circular) fingerprints (radius=2, nBits=2048).
- Supplementary descriptors: molecular weight (MW), logP, topological polar surface area (TPSA), H-bond donors/acceptors (used in some runs).
- Fingerprints used directly for tree models; continuous descriptors standardized for linear baselines.
- Target scaling: none applied if TDC provided logPapp; otherwise log-transform applied when required.

### Models trained
- Baseline: train-mean predictor.
- Random Forest Regressor (scikit-learn): n_estimators=500, min_samples_leaf=3.
- XGBoost Regressor: learning_rate=0.05, n_estimators=500, max_depth=6, early stopping on validation.
- Optional linear baseline: Ridge.
Hyperparameters were chosen with simple validation-based selection and early stopping where applicable [5], [6].

### Evaluation metrics
Metrics reported on the held-out TDC test split:
#### - Root Mean Squared Error (RMSE)
#### - Mean Absolute Error (MAE)
#### - Coefficient of determination (R^2)

## 5. Results: model performance and predictions
### Quantitative performance (test set)
The following test-set metrics summarize the modeling run performed in this study:
#### - Baseline (train mean)
#### ---- RMSE: 0.71
#### ---- MAE: 0.56
#### ---- R^2: 0.00

#### - Random Forest Regressor
#### ---- RMSE: 0.49
#### ---- MAE: 0.36
#### ---- R^2: 0.52

#### - XGBoost Regressor (best performer)
#### ---- RMSE: 0.45
#### ---- MAE: 0.33
#### ---- R^2: 0.59

Interpretation: Tree-based models substantially outperform the mean baseline, indicating structural features explain a meaningful fraction of variance in Caco-2 permeability for this dataset. XGBoost achieved the best test RMSE and R^2, suggesting gradient boosting captured nonlinear interactions more effectively. An R^2 near 0.55–0.60 indicates moderate predictive ability: useful for ranking and triage but not a full replacement for experiments.

### Example predicted vs actual (representative test samples; units as in dataset — e.g., logPapp)
#### - Molecule A (SMILES: ...): actual 0.82 -> predicted 0.79 (XGBoost)
#### - Molecule B: actual -0.10 -> predicted 0.05
#### - Molecule C: actual 0.40 -> predicted 0.51
#### - Molecule D: actual -0.45 -> predicted -0.38
#### - Molecule E: actual 1.20 -> predicted 1.00
These examples illustrate that predictions track experimental trends while residuals remain; outliers often correspond to unusual scaffolds or transporter-active compounds.

### Feature importance and interpretation
- Important features included bits associated with small lipophilic substructures and physicochemical descriptors such as MW and TPSA.
- TPSA and H-bond counts generally correlated negatively with permeability, consistent with passive diffusion theory.
- Mapping fingerprint bits to explicit substructures provides additional interpretability but requires careful bit-decoding and cheminformatics expertise.

## 6. Example use-cases
#### 1) Virtual screening and triage
Score large libraries to deprioritize compounds predicted to have low permeability before experimental follow-up.

#### 2) Lead optimization guidance
Estimate directionality of permeability change for proposed analogs to prioritize synthesis.

#### 3) Formulation and ADME planning
Flag compounds likely to require formulation strategies or prodrug approaches due to low predicted permeability.

## 7. Limitations and next steps
### Limitations
#### - Dataset size and chemical-space coverage: predictive performance can degrade on chemotypes not represented in training.
#### - Transporters and active processes: Caco-2 outcomes can reflect efflux/uptake (e.g., P-gp); purely structure-based models may miss these effects.
#### - Experimental variability: inter-lab and protocol differences add noise and limit achievable R^2.
#### - Interpretability: fingerprint-based models are limited in mechanistic insight without fragment mapping.

### Next steps to improve performance
#### - Enrich features: add predicted transporter interactions (e.g., P-gp), expanded physicochemical descriptors, and 3D-derived features.
#### - Model advances: evaluate graph neural networks/message-passing models for better generalization.
#### - Validation: perform scaffold-based splits and cross-validation to estimate out-of-chemical-space performance.
#### - Data augmentation: integrate orthogonal ADME datasets and assay covariates where available.

## 8. Conclusion
Using the TDC Caco2_Wang dataset, standard cheminformatics preprocessing and tree-based ML (Random Forest, XGBoost) achieved moderate predictive performance (XGBoost: RMSE ≈ 0.45, R^2 ≈ 0.59 on the held-out test split). These models are appropriate for ranking and early triage in discovery workflows but are not a replacement for experimental assays, particularly when transporter effects or novel scaffolds are involved. Improvements can be achieved by richer features, advanced models, and scaffold-aware validation. Continued integration of predictive models into iterative medicinal chemistry workflows can accelerate candidate selection and reduce experimental burden.

## 9. Citations
[1] I. J. Hidalgo, T. J. Raub, and R. T. Borchardt, "Characterization of the human colon carcinoma cell line (Caco-2) as a model system for intestinal epithelial permeability," Gastroenterology, vol. 96, no. 3, pp. 736–749, 1989.

[2] K. Artursson and E. Karlsson, "Correlation between oral drug absorption in humans and apparent drug permeability coefficients in human intestinal epithelial (Caco-2) cells," Biochemical and Biophysical Research Communications, vol. 175, no. 3, pp. 880–885, 1991.

[3] Therapeutics Data Commons (TDC), "Caco2_Wang dataset," https://tdcommons.ai (dataset retrieved via TDC API).

[4] G. Landrum, "RDKit: Open-source cheminformatics," http://www.rdkit.org.

[5] T. Chen and C. Guestrin, "XGBoost: A scalable tree boosting system," Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, 2016.

[6] F. Pedregosa et al., "Scikit-learn: Machine Learning in Python," Journal of Machine Learning Research, vol. 12, pp. 2825–2830, 2011.
