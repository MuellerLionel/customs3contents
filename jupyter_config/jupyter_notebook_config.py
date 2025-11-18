"""
Jupyter configuration for HybridContentsManager with S3 and local file storage.

This configuration sets up:
1. HybridContentsManager to use S3ContentsManager for root directory (S3 storage)
2. LargeFileManager for /local path (local file storage)
3. Extension to fix file downloads for local files
"""
from s3contents import S3ContentsManager
from hybridcontents import HybridContentsManager
from notebook.services.contents.largefilemanager import LargeFileManager

c = get_config()

# Tell Jupyter to use HybridContentsManager for all storage
c.NotebookApp.contents_manager_class = HybridContentsManager

# Configure HybridContentsManager to use both S3 and local file system
c.HybridContentsManager.manager_classes = {
    # Associate the root directory with an S3ContentsManager.
    # This manager will receive all requests that don't fall under any of the
    # other managers.
    "": S3ContentsManager,
    # Associate /local with a LargeFileManager for local file access.
    "local": LargeFileManager,
}

c.HybridContentsManager.manager_kwargs = {
    # Args for root S3ContentsManager.
    "": {
        "access_key_id": "minioadmin",
        "secret_access_key": "minioadmin123",
        "bucket": "jupyter-notebooks",
        "endpoint_url": "http://minio:9000",
        "prefix": "notebooks",
        "signature_version": "s3v4",
    },
    # Args for the LargeFileManager mapped to /local
    "local": {
        "root_dir": "/home/jovyan/work",
    },
}

# Enable the local file download fix extension
# This extension adds a static file handler for /files/local/ to serve files
# from the local directory, allowing file downloads to work with HybridContentsManager
c.ServerApp.jpserver_extensions = {
    's3contents_local_download_fix': True,
}

# Optionally, explicitly configure the local directory (auto-detected from HybridContentsManager if not set)
# c.S3ContentsLocalDownloadFix.local_dir = "/home/jovyan/work"

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
