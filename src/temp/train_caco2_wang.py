#!/usr/bin/env python3
"""
train_caco2_wang.py

Standalone script to download the TDC Caco2_Wang dataset, preprocess, featurize
(morgan fingerprints + simple descriptors), train RandomForest and XGBoost regression
models, evaluate on a held-out test set, save models and predictions, and produce
SHAP summary plot (optional).

Usage:
    python train_caco2_wang.py --out_dir ./caco2_output --seed 42 --use_shap

Dependencies:
    pip install tdc rdkit-pypi scikit-learn xgboost shap pandas numpy joblib matplotlib seaborn

Note: RDKit (rdkit-pypi) may have OS-specific issues; install RDKit from conda if possible.
"""

import os
import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

# RDKit
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors
from rdkit import DataStructs

# TDC
from tdc.single_pred import ADME

# Models & utils
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV, train_test_split, KFold
from sklearn.svm import SVR
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import joblib

# Optional
try:
    import shap
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_SHAP = True
except Exception:
    HAS_SHAP = False


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def load_tdc_dataset(name='Caco2_Wang'):
    logger.info(f"Loading TDC dataset {name}...")
    data = ADME(name=name)
    df = data.get_data()
    # Expect at least 'smiles' and 'Y'
    if 'smiles' not in df.columns or 'Y' not in df.columns:
        raise ValueError('Expected columns "smiles" and "Y" in dataset')
    return data, df


def validate_and_clean(df):
    logger.info("Validating SMILES and cleaning data...")
    df = df.copy()
    df['mol'] = df['smiles'].apply(lambda s: Chem.MolFromSmiles(s) if pd.notnull(s) else None)
    valid = df['mol'].notnull()
    n_invalid = (~valid).sum()
    if n_invalid:
        logger.warning(f"Dropping {n_invalid} rows with invalid SMILES")
    df = df[valid].reset_index(drop=True)

    # Drop rows with missing labels
    before = len(df)
    df = df[df['Y'].notnull()].reset_index(drop=True)
    logger.info(f"Rows before label drop: {before}; after: {len(df)}")

    # Drop exact duplicates by SMILES (keep first)
    before = len(df)
    df = df.drop_duplicates(subset='smiles').reset_index(drop=True)
    logger.info(f"Dropped {before - len(df)} exact duplicate SMILES")

    return df


def featurize_df(df, n_bits=2048):
    logger.info("Featurizing molecules (Morgan fingerprints + descriptors)")
    fps = []
    descs = []
    mols = []
    for smi in df['smiles']:
        mol = Chem.MolFromSmiles(smi)
        mols.append(mol)
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=n_bits)
        arr = np.zeros((n_bits,), dtype=np.int8)
        DataStructs.ConvertToNumpyArray(fp, arr)
        fps.append(arr)
        descs.append([
            Descriptors.MolWt(mol),
            Descriptors.MolLogP(mol),
            Descriptors.TPSA(mol),
            Descriptors.NumHDonors(mol),
            Descriptors.NumHAcceptors(mol),
            Descriptors.NumRotatableBonds(mol)
        ])
    X_fp = np.vstack(fps)
    X_desc = np.array(descs, dtype=float)
    X = np.hstack([X_fp, X_desc])
    desc_names = ['MolWt', 'MolLogP', 'TPSA', 'HDonors', 'HAcceptors', 'RotBonds']
    feature_names = [f'FP_{i}' for i in range(X_fp.shape[1])] + desc_names
    return X, feature_names


def try_scaffold_split(tdc_data, df):
    """Attempt to get scaffold split via TDC helper. Returns indices or None."""
    try:
        logger.info("Attempting scaffold split using TDC helper...")
        splits = tdc_data.get_split()
        # tdc.get_split returns dict of indices or masks under keys train/val/test
        if 'train' in splits and 'test' in splits:
            return splits
    except Exception as e:
        logger.warning("TDC scaffold split not available or failed: %s", e)
    return None


def compute_metrics(y_true, y_pred):
    rmse = mean_squared_error(y_true, y_pred, squared=False)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    return {'RMSE': float(rmse), 'MAE': float(mae), 'R2': float(r2)}


def train_and_evaluate(X_train, y_train, X_test, y_test, feature_names, out_dir, seed=42, run_shap=False):
    results = {}

    # Standard scaling for non-tree models (we'll use it for SVR optional)
    scaler = StandardScaler()
    scaler.fit(X_train)
    joblib.dump(scaler, os.path.join(out_dir, 'scaler.pkl'))

    # Random Forest
    logger.info("Training RandomForestRegressor (GridSearchCV)...")
    rf = RandomForestRegressor(random_state=seed, n_jobs=-1)
    rf_params = {
        'n_estimators': [100, 300],
        'max_depth': [None, 10, 20]
    }
    rf_cv = GridSearchCV(rf, rf_params, cv=3, scoring='neg_root_mean_squared_error', n_jobs=-1, verbose=1)
    rf_cv.fit(X_train, y_train)
    logger.info(f"RF best params: {rf_cv.best_params_}")
    rf_best = rf_cv.best_estimator_
    y_pred_rf = rf_best.predict(X_test)
    metrics_rf = compute_metrics(y_test, y_pred_rf)
    results['RandomForest'] = metrics_rf
    joblib.dump(rf_best, os.path.join(out_dir, 'model_random_forest.pkl'))
    pd.DataFrame({'smiles': test_df['smiles'], 'Y': y_test, 'pred': y_pred_rf}).to_csv(os.path.join(out_dir, 'predictions_random_forest.csv'), index=False)

    # XGBoost
    logger.info("Training XGBoostRegressor (GridSearchCV)...")
    xg = xgb.XGBRegressor(objective='reg:squarederror', random_state=seed, n_jobs=-1)
    xg_params = {
        'n_estimators': [100, 300],
        'learning_rate': [0.01, 0.1],
        'max_depth': [3, 6]
    }
    xg_cv = GridSearchCV(xg, xg_params, cv=3, scoring='neg_root_mean_squared_error', n_jobs=-1, verbose=1)
    xg_cv.fit(X_train, y_train)
    logger.info(f"XGBoost best params: {xg_cv.best_params_}")
    xg_best = xg_cv.best_estimator_
    y_pred_xg = xg_best.predict(X_test)
    metrics_xg = compute_metrics(y_test, y_pred_xg)
    results['XGBoost'] = metrics_xg
    joblib.dump(xg_best, os.path.join(out_dir, 'model_xgboost.pkl'))
    pd.DataFrame({'smiles': test_df['smiles'], 'Y': y_test, 'pred': y_pred_xg}).to_csv(os.path.join(out_dir, 'predictions_xgboost.csv'), index=False)

    # Optional: SVR baseline (scaled)
    logger.info("Training SVR baseline (scaled features, small grid)...")
    svr = SVR()
    svr_params = {'C': [1.0, 10.0], 'gamma': ['scale', 'auto']}
    svr_cv = GridSearchCV(svr, svr_params, cv=3, scoring='neg_root_mean_squared_error', n_jobs=-1, verbose=1)
    svr_cv.fit(scaler.transform(X_train), y_train)
    svr_best = svr_cv.best_estimator_
    y_pred_svr = svr_best.predict(scaler.transform(X_test))
    metrics_svr = compute_metrics(y_test, y_pred_svr)
    results['SVR'] = metrics_svr
    joblib.dump(svr_best, os.path.join(out_dir, 'model_svr.pkl'))
    pd.DataFrame({'smiles': test_df['smiles'], 'Y': y_test, 'pred': y_pred_svr}).to_csv(os.path.join(out_dir, 'predictions_svr.csv'), index=False)

    # Save metrics
    with open(os.path.join(out_dir, 'metrics.json'), 'w') as f:
        json.dump(results, f, indent=2)

    logger.info("Training complete. Metrics:")
    logger.info(json.dumps(results, indent=2))

    # SHAP (optional)
    if run_shap:
        if not HAS_SHAP:
            logger.warning('SHAP not available in environment; skipping SHAP analysis')
        else:
            logger.info('Computing SHAP values for XGBoost best model...')
            explainer = shap.TreeExplainer(xg_best)
            # For speed, take a subset of test or training data
            sample_X = pd.DataFrame(X_test, columns=feature_names)
            shap_vals = explainer.shap_values(sample_X)
            plt.figure(figsize=(8, 6))
            shap.summary_plot(shap_vals, sample_X, show=False, max_display=30)
            plt.tight_layout()
            shp_path = os.path.join(out_dir, 'shap_summary.png')
            plt.savefig(shp_path, dpi=300)
            plt.close()
            logger.info(f'SHAP summary saved to {shp_path}')

    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train Caco-2 permeability models on TDC Caco2_Wang')
    parser.add_argument('--out_dir', type=str, default='./caco2_output', help='Directory to save outputs')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--test_size', type=float, default=0.2, help='Proportion for test set (if not using TDC split)')
    parser.add_argument('--use_shap', action='store_true', help='Compute SHAP summary plot for XGBoost')
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load dataset
    tdc_data, raw_df = load_tdc_dataset('Caco2_Wang')

    # Clean
    df = validate_and_clean(raw_df)

    # Attempt to use TDC provided split (scaffold) if available
    splits = None
    try:
        splits = tdc_data.get_split()
    except Exception:
        splits = None

    if splits is not None and 'train' in splits and 'test' in splits:
        # splits are indices (list-like) into the original df from TDC.get_data(); map to our cleaned df by smiles
        logger.info('Using TDC provided split indices')
        # TDC indices correspond to positions in raw_df. We'll extract smiles for each split and then select cleaned rows that match.
        train_idxs = splits['train']
        val_idxs = splits.get('val', [])
        test_idxs = splits['test']
        train_smiles = set(raw_df.loc[train_idxs, 'smiles'])
        test_smiles = set(raw_df.loc[test_idxs, 'smiles'])

        train_df = df[df['smiles'].isin(train_smiles)].reset_index(drop=True)
        test_df = df[df['smiles'].isin(test_smiles)].reset_index(drop=True)
        # if val present, also create val_df (not used separately here)
        val_df = df[df['smiles'].isin(set(raw_df.loc[val_idxs, 'smiles']))].reset_index(drop=True) if len(val_idxs) else None
        # If splits are empty due to cleaning, fall back to random
        if len(train_df) < 10 or len(test_df) < 10:
            logger.warning('TDC split produced too-small train/test after cleaning. Falling back to random split')
            train_df, test_df = train_test_split(df, test_size=args.test_size, random_state=args.seed)
    else:
        logger.info('No TDC split available; using random train/test split')
        train_df, test_df = train_test_split(df, test_size=args.test_size, random_state=args.seed)

    logger.info(f'Train size: {len(train_df)}; Test size: {len(test_df)}')

    # Featurize
    X_train, feature_names = featurize_df(train_df)
    X_test, _ = featurize_df(test_df)
    y_train = train_df['Y'].values.astype(float)
    y_test = test_df['Y'].values.astype(float)

    # Persist basic data
    train_df[['smiles', 'Y']].to_csv(out_dir / 'train_smiles.csv', index=False)
    test_df[['smiles', 'Y']].to_csv(out_dir / 'test_smiles.csv', index=False)

    # Train and evaluate
    results = train_and_evaluate(X_train, y_train, X_test, y_test, feature_names, str(out_dir), seed=args.seed, run_shap=args.use_shap)

    logger.info('All done. Outputs saved to %s', out_dir)
