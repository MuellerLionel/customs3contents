FROM jupyter/scipy-notebook:latest

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

USER $NB_UID

# Install s3contents and hybridcontents
RUN pip install --no-cache-dir \
    s3contents \
    hybridcontents \
    boto3

# Create jupyter config directory
RUN mkdir -p /home/jovyan/.jupyter

# Copy configuration file
COPY jupyter_config/jupyter_notebook_config.py /home/jovyan/.jupyter/jupyter_notebook_config.py

# Copy and install the local file handler extension to site-packages
COPY jupyter_config/local_file_handler_extension.py /tmp/local_file_handler_extension.py
USER root
RUN python -c "import site; import shutil; shutil.copy('/tmp/local_file_handler_extension.py', site.getsitepackages()[0] + '/local_file_handler_extension.py')" && \
    rm /tmp/local_file_handler_extension.py && \
    chown -R $NB_UID:$NB_GID /home/jovyan/.jupyter && \
    python -c "import site; import os; os.chown(site.getsitepackages()[0] + '/local_file_handler_extension.py', $NB_UID, $NB_GID)" && \
    chmod +x /usr/local/bin/start-notebook.d/*.sh 2>/dev/null || true
USER $NB_UID

