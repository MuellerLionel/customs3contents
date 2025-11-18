FROM jupyter/pyspark-notebook:latest

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

USER $NB_UID

# Install s3contents, hybridcontents, and the local download fix extension
RUN pip install --no-cache-dir \
    s3contents \
    hybridcontents \
    boto3

# Install the local download fix extension by copying to site-packages
# This works in corporate environments without external package repositories
COPY s3contents_local_download_fix.py /tmp/s3contents_local_download_fix.py
USER root
RUN python -c "import site; import shutil; import os; \
    target_dir = site.getsitepackages()[0]; \
    shutil.copy('/tmp/s3contents_local_download_fix.py', os.path.join(target_dir, 's3contents_local_download_fix.py')); \
    os.chown(os.path.join(target_dir, 's3contents_local_download_fix.py'), $NB_UID, $NB_GID)" && \
    rm /tmp/s3contents_local_download_fix.py
USER $NB_UID

# Create jupyter config directory
RUN mkdir -p /home/jovyan/.jupyter

# Copy configuration file
COPY jupyter_config/jupyter_notebook_config.py /home/jovyan/.jupyter/jupyter_notebook_config.py

# Ensure proper ownership
USER root
RUN chown -R $NB_UID:$NB_GID /home/jovyan/.jupyter
USER $NB_UID
