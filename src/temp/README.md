Caco2_Wang ML Notebook

Files included:
- Caco2_Wang_ML_Notebook.ipynb: Jupyter notebook containing the full report (markdown) and reproducible code cells to load the TDC Caco2_Wang dataset, featurize molecules, train Random Forest/XGBoost, optionally train a GNN, evaluate metrics, and save predictions/models.
- environment.yml: Conda environment file recommended for reproducible installation (RDKit and PyTorch via conda-forge and pytorch channels).
- requirements.txt: Pip-installable package list (note: RDKit and PyG recommended via conda; this file lists pip fallbacks).
- Dockerfile: CPU-based Dockerfile that installs Miniconda, creates the conda env, copies the notebook, and starts Jupyter Lab.
- GPU_Dockerfile_CUDA11.7: GPU-enabled Dockerfile based on nvidia/cuda image with instructions to install PyG wheels compatible with PyTorch/CUDA.

Quick start (recommended: conda)
1. Create conda environment:
   conda env create -f environment.yml
   conda activate caco2_env
2. Launch Jupyter Lab and open the notebook:
   jupyter lab Caco2_Wang_ML_Notebook.ipynb

Alternative (Docker, CPU-only):
1. Build Docker image:
   docker build -t caco2_ml -f Dockerfile .
2. Run container and map port 8888:
   docker run -p 8888:8888 -v $(pwd):/workspace caco2_ml
3. Open http://localhost:8888 in your browser (no token set by default in Dockerfile).\n
GPU Docker (requires NVIDIA Container Toolkit):
1. Build GPU image:
   docker build -t caco2_ml_gpu -f GPU_Dockerfile_CUDA11.7 .
2. Run with nvidia runtime:
   docker run --gpus all -p 8888:8888 -v $(pwd):/workspace caco2_ml_gpu

Hardware recommendations and runtime
- Random Forest / XGBoost / LightGBM: CPU is sufficient; typical runtimes minutes to tens of minutes depending on dataset size and hyperparameter search.
- GNN: GPU recommended. Training on CPU can be slow. Expect tens of minutes to hours on GPU depending on epochs and model complexity.
- Disk: allow several GB for conda packages and model outputs.

RDKit and PyTorch Geometric notes
- RDKit: conda-forge builds are recommended: conda install -c conda-forge rdkit
- PyTorch: follow https://pytorch.org for the correct pip/conda install command matching your CUDA version.
- PyTorch Geometric (PyG): follow https://pytorch-geometric.readthedocs.io/ for wheels matching PyTorch/CUDA. Installation commands are included as comments in environment.yml and GPU_Dockerfile_CUDA11.7.

Files produced by the notebook (after running):
- saved_models/: directory containing saved model files (rf_model.joblib, gb_model.joblib, gnn_model.pt if GNN enabled).
- caco2_predictions.csv: merged per-compound predictions from trained models on the held-out test set.
- caco2_predictions_rf.csv, caco2_predictions_gb.csv, caco2_predictions_gnn.csv: per-model predictions.
- caco2_applicability.csv: applicability-domain metric (nearest Tanimoto similarity).
- caco2_summary_metrics.csv: summary metrics (RMSE, MAE, R2) for models trained.

Contact / Next steps
- If you want an environment.yml tailored to CPU-only use, a GPU Dockerfile for a specific CUDA version, or the notebook with USE_GNN enabled by default, request it and it will be provided.
