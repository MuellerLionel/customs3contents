# S3Contents Local File Download Fix

A **corporate-friendly** Jupyter Server extension that fixes file download issues when using `HybridContentsManager` with local file storage in `s3contents` setups. This solution uses **only local files** - no external package repositories or GitHub dependencies required.

## Problem

When using `s3contents` with `hybridcontents` to access both S3 and local files, file downloads from the local directory (`/local` path) fail because JupyterLab cannot properly serve files from the local filesystem through the HybridContentsManager.

## Solution

This extension adds a static file handler endpoint (`/files/local/`) that serves files from the local directory configured in HybridContentsManager, enabling proper file downloads. The solution is designed for **corporate environments** where external package repositories may be restricted.

## Features

- ✅ **Corporate-friendly** - No pip/GitHub dependencies, uses only local files
- ✅ **Zero configuration** - Auto-detects local directory from HybridContentsManager config
- ✅ **Secure** - Path traversal protection and proper security checks
- ✅ **KubeSpawner/JupyterHub ready** - Works seamlessly with Kubernetes deployments
- ✅ **Simple integration** - Just add a few lines to your existing Dockerfile

---

## Corporate Environment Setup for JupyterHub/KubeSpawner

This guide will help you integrate the extension into your existing custom JupyterLab Dockerfile and deploy it via KubeSpawner in a JupyterHub environment.

### Prerequisites

- Existing custom JupyterLab Dockerfile
- JupyterHub with KubeSpawner configured
- Access to build Docker images
- Kubernetes cluster with JupyterHub deployed

### Step 1: Get the Extension File

Download or copy the `s3contents_local_download_fix.py` file to your build context:

```bash
# Option 1: Clone this repository
git clone <repository-url>
cp s3contents_local_download_fix.py /path/to/your/docker/build/context/

# Option 2: Download just the file
# Copy s3contents_local_download_fix.py to your Docker build context directory
```

**Important**: Place the file in the same directory as your Dockerfile (or a subdirectory that will be copied).

### Step 2: Integrate into Your Dockerfile

Add the following to your existing JupyterLab Dockerfile. The extension will be installed by copying it to site-packages (no external dependencies needed):

```dockerfile
# ... your existing Dockerfile content ...

# Install the local download fix extension
# This works in corporate environments without external package repositories
COPY s3contents_local_download_fix.py /tmp/s3contents_local_download_fix.py
USER root
RUN python -c "import site; import shutil; import os; \
    target_dir = site.getsitepackages()[0]; \
    shutil.copy('/tmp/s3contents_local_download_fix.py', os.path.join(target_dir, 's3contents_local_download_fix.py')); \
    os.chown(os.path.join(target_dir, 's3contents_local_download_fix.py'), $NB_UID, $NB_GID)" && \
    rm /tmp/s3contents_local_download_fix.py
USER $NB_UID

# ... rest of your Dockerfile ...
```

**Note**: Replace `$NB_UID` and `$NB_GID` with your actual user/group IDs if they differ. For JupyterHub, these are typically set by the base image.

### Step 3: Add Configuration to Your Jupyter Config

You need to add the extension configuration to your Jupyter configuration. There are two approaches:

#### Option A: Add to Existing Config File (Recommended)

If you already have a `jupyter_notebook_config.py` or `jupyter_server_config.py` that you copy into the image:

```dockerfile
# In your Dockerfile, copy your config file
COPY jupyter_notebook_config.py /home/jovyan/.jupyter/jupyter_notebook_config.py
```

Then add this to your `jupyter_notebook_config.py`:

```python
# ... your existing configuration ...

# Enable the local file download fix extension
c.ServerApp.jpserver_extensions = {
    's3contents_local_download_fix': True,
}

# Explicitly load the extension by hooking into web app initialization
# This ensures the extension loads even if auto-discovery doesn't work
import jupyter_server.serverapp

_original_init_webapp = jupyter_server.serverapp.ServerApp.init_webapp

def _patched_init_webapp(self, *args, **kwargs):
    """Patched init_webapp that loads our extension."""
    result = _original_init_webapp(self, *args, **kwargs)
    # Load our extension after web app is initialized
    try:
        import s3contents_local_download_fix
        s3contents_local_download_fix.load_jupyter_server_extension(self)
    except Exception as e:
        self.log.warning(f"Failed to load s3contents_local_download_fix extension: {e}")
    return result

jupyter_server.serverapp.ServerApp.init_webapp = _patched_init_webapp
```

#### Option B: Create Config File in Dockerfile

If you don't have a separate config file, create one in your Dockerfile:

```dockerfile
# Create jupyter config directory
RUN mkdir -p /home/jovyan/.jupyter

# Create configuration file with extension setup
RUN echo 'c = get_config()' > /home/jovyan/.jupyter/jupyter_notebook_config.py && \
    echo 'c.ServerApp.jpserver_extensions = {"s3contents_local_download_fix": True}' >> /home/jovyan/.jupyter/jupyter_notebook_config.py && \
    echo 'import jupyter_server.serverapp' >> /home/jovyan/.jupyter/jupyter_notebook_config.py && \
    echo '_original_init_webapp = jupyter_server.serverapp.ServerApp.init_webapp' >> /home/jovyan/.jupyter/jupyter_notebook_config.py && \
    echo 'def _patched_init_webapp(self, *args, **kwargs):' >> /home/jovyan/.jupyter/jupyter_notebook_config.py && \
    echo '    result = _original_init_webapp(self, *args, **kwargs)' >> /home/jovyan/.jupyter/jupyter_notebook_config.py && \
    echo '    try:' >> /home/jovyan/.jupyter/jupyter_notebook_config.py && \
    echo '        import s3contents_local_download_fix' >> /home/jovyan/.jupyter/jupyter_notebook_config.py && \
    echo '        s3contents_local_download_fix.load_jupyter_server_extension(self)' >> /home/jovyan/.jupyter/jupyter_notebook_config.py && \
    echo '    except Exception as e:' >> /home/jovyan/.jupyter/jupyter_notebook_config.py && \
    echo '        self.log.warning(f"Failed to load extension: {e}")' >> /home/jovyan/.jupyter/jupyter_notebook_config.py && \
    echo '    return result' >> /home/jovyan/.jupyter/jupyter_notebook_config.py && \
    echo 'jupyter_server.serverapp.ServerApp.init_webapp = _patched_init_webapp' >> /home/jovyan/.jupyter/jupyter_notebook_config.py

# Ensure proper ownership
USER root
RUN chown -R $NB_UID:$NB_GID /home/jovyan/.jupyter
USER $NB_UID
```

**Better approach**: Create a proper Python config file and copy it:

```dockerfile
# Create config directory
RUN mkdir -p /home/jovyan/.jupyter

# Copy your config file (create this file in your build context)
COPY jupyter_notebook_config.py /home/jovyan/.jupyter/jupyter_notebook_config.py

# Ensure proper ownership
USER root
RUN chown -R $NB_UID:$NB_GID /home/jovyan/.jupyter
USER $NB_UID
```

### Step 4: Complete Example Dockerfile

Here's a complete example showing how to integrate everything:

```dockerfile
FROM jupyter/scipy-notebook:latest

USER root

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

USER $NB_UID

# Install your Python packages
RUN pip install --no-cache-dir \
    s3contents \
    hybridcontents \
    boto3 \
    # ... your other packages ...

# Install the local download fix extension
# Copy the extension file to site-packages
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

# Copy your Jupyter configuration file
COPY jupyter_notebook_config.py /home/jovyan/.jupyter/jupyter_notebook_config.py

# Ensure proper ownership
USER root
RUN chown -R $NB_UID:$NB_GID /home/jovyan/.jupyter
USER $NB_UID

# ... any other customizations ...
```

### Step 5: Build Your Docker Image

Build your image:

```bash
# Navigate to your Docker build context
cd /path/to/your/docker/build/context

# Build the image
docker build -t your-registry/jupyterlab-s3:latest .

# Tag for your registry (if needed)
docker tag your-registry/jupyterlab-s3:latest your-registry/jupyterlab-s3:v1.0.0

# Push to your container registry
docker push your-registry/jupyterlab-s3:latest
```

### Step 6: Configure JupyterHub to Use Your Image

Update your JupyterHub configuration to use the new image. In your `config.yaml` or Helm values:

```yaml
singleuser:
  image:
    name: your-registry/jupyterlab-s3
    tag: latest
  # ... other singleuser config ...
```

Or if using KubeSpawner directly:

```python
c.KubeSpawner.image = 'your-registry/jupyterlab-s3:latest'
```

### Step 7: Deploy and Verify

1. **Deploy/Update JupyterHub:**
   ```bash
   # If using Helm
   helm upgrade --install jupyterhub jupyterhub/jupyterhub \
     --namespace jupyterhub \
     --create-namespace \
     -f config.yaml
   
   # Or apply your Kubernetes manifests
   kubectl apply -f jupyterhub-config.yaml
   ```

2. **Verify Extension Loaded:**
   - Start a JupyterLab instance via JupyterHub
   - Check the pod logs:
     ```bash
     kubectl logs -n jupyterhub <pod-name> | grep s3contents_local_download_fix
     ```
   - You should see: `s3contents_local_download_fix: Extension loaded successfully. Serving files from /path/to/local at /files/local/`

3. **Test File Downloads:**
   - Navigate to `/local` directory in JupyterLab
   - Create or upload a file
   - Right-click and download - it should work! ✅

---

## Complete Configuration Example

Here's a complete `jupyter_notebook_config.py` that sets up HybridContentsManager with the extension:

```python
"""
Jupyter configuration for HybridContentsManager with S3 and local file storage.
Configured for JupyterHub/KubeSpawner deployment.
"""
from s3contents import S3ContentsManager
from hybridcontents import HybridContentsManager
from notebook.services.contents.largefilemanager import LargeFileManager

c = get_config()

# Tell Jupyter to use HybridContentsManager for all storage
c.NotebookApp.contents_manager_class = HybridContentsManager

# Configure HybridContentsManager to use both S3 and local file system
c.HybridContentsManager.manager_classes = {
    # Root directory uses S3ContentsManager (S3 storage)
    "": S3ContentsManager,
    # /local path uses LargeFileManager (local file storage)
    "local": LargeFileManager,
}

c.HybridContentsManager.manager_kwargs = {
    # S3 configuration
    # In production, use environment variables or secrets
    "": {
        "access_key_id": os.environ.get("S3_ACCESS_KEY_ID", "your-s3-access-key"),
        "secret_access_key": os.environ.get("S3_SECRET_ACCESS_KEY", "your-s3-secret-key"),
        "bucket": os.environ.get("S3_BUCKET", "your-bucket-name"),
        "endpoint_url": os.environ.get("S3_ENDPOINT_URL", "http://your-s3-endpoint:9000"),
        "prefix": os.environ.get("S3_PREFIX", "notebooks"),
        "signature_version": "s3v4",
    },
    # Local file system configuration
    # The extension will auto-detect this path
    "local": {
        "root_dir": os.environ.get("LOCAL_ROOT_DIR", "/home/jovyan/work"),
    },
}

# Enable the local file download fix extension
c.ServerApp.jpserver_extensions = {
    's3contents_local_download_fix': True,
}

# Explicitly load the extension by hooking into web app initialization
import jupyter_server.serverapp

_original_init_webapp = jupyter_server.serverapp.ServerApp.init_webapp

def _patched_init_webapp(self, *args, **kwargs):
    """Patched init_webapp that loads our extension."""
    result = _original_init_webapp(self, *args, **kwargs)
    # Load our extension after web app is initialized
    try:
        import s3contents_local_download_fix
        s3contents_local_download_fix.load_jupyter_server_extension(self)
    except Exception as e:
        self.log.warning(f"Failed to load s3contents_local_download_fix extension: {e}")
    return result

jupyter_server.serverapp.ServerApp.init_webapp = _patched_init_webapp
```

**Note**: Don't forget to add `import os` at the top if using environment variables.

---

## JupyterHub/KubeSpawner Specific Configuration

### Using Environment Variables

For JupyterHub deployments, it's recommended to use environment variables for configuration:

```yaml
# In your JupyterHub config.yaml
singleuser:
  image:
    name: your-registry/jupyterlab-s3
    tag: latest
  extraEnv:
    S3_ACCESS_KEY_ID: "your-access-key"
    S3_SECRET_ACCESS_KEY: "your-secret-key"
    S3_BUCKET: "your-bucket"
    S3_ENDPOINT_URL: "http://s3-endpoint:9000"
    LOCAL_ROOT_DIR: "/home/jovyan/work"
```

Or use Kubernetes secrets:

```yaml
singleuser:
  extraEnv:
    S3_ACCESS_KEY_ID:
      valueFrom:
        secretKeyRef:
          name: s3-credentials
          key: access-key-id
    S3_SECRET_ACCESS_KEY:
      valueFrom:
        secretKeyRef:
          name: s3-credentials
          key: secret-access-key
```

### Volume Mounts for Local Files

If you need persistent local storage in Kubernetes:

```yaml
singleuser:
  storage:
    type: dynamic
    capacity: 10Gi
    # This will mount to /home/jovyan/work by default
```

Or use a PVC:

```yaml
singleuser:
  storage:
    type: static
    staticPvcName: jupyterhub-user-pvc
```

---

## Customization

### Change Local Directory Path

The extension automatically detects the local directory from your HybridContentsManager configuration. If you need to override it:

```python
c.S3ContentsLocalDownloadFix.local_dir = "/custom/path/to/local/files"
```

### Change URL Prefix

By default, files are served at `/files/local/`. To change this:

```python
c.S3ContentsLocalDownloadFix.url_prefix = "/custom/prefix/"
```

---

## Troubleshooting

### Extension Not Loading

**Check pod logs:**
```bash
kubectl logs -n jupyterhub <pod-name> | grep s3contents_local_download_fix
```

**Verify the extension file exists in the image:**
```bash
kubectl exec -n jupyterhub <pod-name> -- python -c "import s3contents_local_download_fix; print('OK')"
```

**Check configuration:**
```bash
kubectl exec -n jupyterhub <pod-name> -- cat /home/jovyan/.jupyter/jupyter_notebook_config.py | grep jpserver_extensions
```

### Files Still Not Downloading

1. **Verify local directory path** is correct in your HybridContentsManager config
2. **Check that files exist** in the local directory
3. **Ensure the extension is enabled** in your config file
4. **Check pod logs** for handler registration messages:
   ```bash
   kubectl logs -n jupyterhub <pod-name> | grep "Extension loaded successfully"
   ```

### Permission Errors

Ensure the Jupyter process has read access to the local directory:

```bash
# Check permissions in the pod
kubectl exec -n jupyterhub <pod-name> -- ls -la /home/jovyan/work

# Check volume mount
kubectl describe pod -n jupyterhub <pod-name> | grep -A 5 "Mounts:"
```

### Testing the Endpoint Directly

Test if the extension endpoint is working from within a pod:

```bash
# Create a test file
kubectl exec -n jupyterhub <pod-name> -- bash -c "echo 'Test content' > /home/jovyan/work/test.txt"

# Test the endpoint (port-forward first if needed)
kubectl port-forward -n jupyterhub <pod-name> 8888:8888
curl http://localhost:8888/files/local/test.txt
```

---

## How It Works

1. **Extension Registration**: The extension registers a Tornado request handler at `/files/local/(.*)`
2. **File Requests**: When JupyterLab requests a file download from the local directory, it uses this endpoint
3. **Security Checks**: The handler validates the file path (prevents directory traversal attacks)
4. **File Serving**: The file is served with proper headers (Content-Type, Content-Disposition, etc.)
5. **Streaming**: Files are streamed in chunks for efficient memory usage

## Architecture

```
┌─────────────────┐
│   JupyterHub    │
│  (KubeSpawner)  │
└────────┬────────┘
         │
         │ Spawns pods with
         │ custom JupyterLab image
         │
┌────────▼────────┐
│   JupyterLab    │
│   (in Pod)      │
└────────┬────────┘
         │
         │ Uses s3contents + hybridcontents
         │ + s3contents_local_download_fix
         │
┌────────▼────────┐
│  HybridContents │
│     Manager     │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────┐
│  S3   │ │  Local  │
│       │ │  Files  │
│       │ │ /local  │
└───────┘ └─────────┘
```

## Security Features

- **Path Traversal Protection**: Normalized paths ensure files can only be accessed within the configured directory
- **CSRF Protection**: Inherits Jupyter's default CSRF protection via RequestHandler
- **File Validation**: Checks that paths exist and are files (not directories)
- **Error Handling**: Proper error responses without exposing internal paths
- **Permission Checks**: Validates file existence and permissions before serving

## Files You Need

For a **corporate environment setup**, you only need:

1. **`s3contents_local_download_fix.py`** - The extension file (copy to your Docker build context)
2. **Configuration snippet** - Add to your `jupyter_notebook_config.py`

That's it! No external dependencies, no package repositories needed.

## Testing

The solution has been tested and verified to work with:
- ✅ File downloads from `/local` directory
- ✅ Nested directory structures
- ✅ Files with special characters
- ✅ Path traversal protection
- ✅ Error handling (404 for missing files)
- ✅ Proper HTTP headers (Content-Type, Content-Disposition, Content-Length)
- ✅ JupyterHub/KubeSpawner deployments

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review pod logs for error messages
3. Verify the extension file is in the correct location in your image
4. Ensure your configuration matches the examples provided
5. Verify your Docker image was built correctly and pushed to your registry

## License

This project is provided as-is for use with JupyterLab and s3contents setups.
