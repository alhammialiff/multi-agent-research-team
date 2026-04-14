# Non-GPU Dockerfile for Caco2_Wang ML Notebook (uses Miniconda and conda-forge RDKit)
# This image is CPU-only and suitable for running Random Forest / XGBoost pipelines.

FROM python:3.9-slim
LABEL maintainer="data-science-team@example.com"
ENV DEBIAN_FRONTEND=noninteractive

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget ca-certificates bzip2 git build-essential libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Install Miniconda
ENV CONDA_DIR=/opt/conda
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh \
    && /bin/bash /tmp/miniconda.sh -b -p $CONDA_DIR \
    && rm /tmp/miniconda.sh
ENV PATH=$CONDA_DIR/bin:$PATH

# Copy environment.yml and create conda env (uses conda-forge RDKit)
COPY environment.yml /tmp/environment.yml
RUN conda env create -f /tmp/environment.yml && conda clean -afy

SHELL ["/bin/bash", "-lc"]

# Activate environment and install PyG CPU wheels if desired (optional)
# Note: For CPU-only PyG, you may install torch-geometric with CPU wheels following PyG docs.

# Copy notebook and start Jupyter Lab
WORKDIR /workspace
COPY Caco2_Wang_ML_Notebook.ipynb /workspace/Caco2_Wang_ML_Notebook.ipynb
RUN mkdir -p /workspace/saved_models
EXPOSE 8888
CMD source activate caco2_env && jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token=''

# Notes:
# - For GPU-enabled containers, use the GPU Dockerfile (GPU_Dockerfile_CUDA11.7) which is based on an nvidia/cuda image.
# - The image size may be several GB due to conda package installations. Use environment.yml with pinned versions for reproducibility.
