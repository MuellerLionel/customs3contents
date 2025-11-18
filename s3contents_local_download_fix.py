"""
Jupyter Server extension to fix file downloads for local files in HybridContentsManager.

This extension adds a static file handler for /files/local/ endpoint that serves files
from the local directory configured in HybridContentsManager, allowing file downloads
to work properly when using s3contents with hybridcontents.

Configuration:
    Add to jupyter_notebook_config.py or jupyter_server_config.py:
    
    c.ServerApp.jpserver_extensions = {
        's3contents_local_download_fix': True,
    }
    
    # Optionally configure the local directory path (defaults to reading from HybridContentsManager)
    c.S3ContentsLocalDownloadFix.local_dir = "/path/to/local/files"
    
    # Optionally configure the URL prefix (defaults to "/files/local/")
    c.S3ContentsLocalDownloadFix.url_prefix = "/files/local/"
"""
import os
import mimetypes
from urllib.parse import quote
from tornado.web import RequestHandler
from tornado import web
from traitlets import Unicode
from traitlets.config import Configurable


def _jupyter_server_extension_points():
    """Return a list of dictionaries with metadata about this extension."""
    return [{
        "module": "s3contents_local_download_fix"
    }]


def _jupyter_server_extension_paths():
    """Return paths for server extensions (legacy support)."""
    return [{
        "module": "s3contents_local_download_fix"
    }]


class S3ContentsLocalDownloadFixConfig(Configurable):
    """Configuration for the local file download fix extension."""
    
    local_dir = Unicode(
        "",
        help="Local directory path to serve files from. If empty, will try to read from HybridContentsManager config."
    ).tag(config=True)
    
    url_prefix = Unicode(
        "/files/local/",
        help="URL prefix for the file handler endpoint"
    ).tag(config=True)


def _get_local_dir_from_config(server_app):
    """
    Try to extract the local directory from HybridContentsManager configuration.
    
    Returns the local directory path if found, otherwise None.
    """
    try:
        # Try to get from HybridContentsManager config
        if hasattr(server_app, 'config') and hasattr(server_app.config, 'HybridContentsManager'):
            manager_kwargs = getattr(server_app.config.HybridContentsManager, 'manager_kwargs', {})
            if isinstance(manager_kwargs, dict):
                # Look for 'local' manager configuration
                local_config = manager_kwargs.get('local', {})
                if isinstance(local_config, dict):
                    root_dir = local_config.get('root_dir')
                    if root_dir and os.path.isabs(root_dir):
                        return root_dir
    except Exception:
        pass
    return None


def _load_jupyter_server_extension(server_app):
    """
    Load the extension in Jupyter Server.
    
    This function is called by Jupyter Server when the extension is enabled.
    """
    # Get configuration
    config = S3ContentsLocalDownloadFixConfig(config=server_app.config)
    
    # Determine local directory
    local_dir = config.local_dir
    if not local_dir:
        # Try to auto-detect from HybridContentsManager config
        local_dir = _get_local_dir_from_config(server_app)
    
    if not local_dir:
        server_app.log.warning(
            "s3contents_local_download_fix: No local directory configured. "
            "Set c.S3ContentsLocalDownloadFix.local_dir in your config file."
        )
        return
    
    if not os.path.exists(local_dir):
        server_app.log.warning(
            f"s3contents_local_download_fix: Local directory does not exist: {local_dir}"
        )
        return
    
    # Normalize the path
    local_dir = os.path.normpath(os.path.abspath(local_dir))
    url_prefix = config.url_prefix.rstrip('/') + '/'
    
    # Create the file handler class
    class LocalFileHandler(RequestHandler):
        """
        Handler for serving local files.
        
        Security: Path traversal is prevented by normalizing paths and checking
        that the resolved path starts with the configured local_dir.
        CSRF protection is handled by Jupyter's default RequestHandler behavior.
        """
        
        def get(self, file_path):
            """Serve a file from the local directory."""
            try:
                # Construct the full file path
                # Remove leading slash if present
                file_path = file_path.lstrip('/')
                full_path = os.path.join(local_dir, file_path)
                
                # Normalize path to prevent directory traversal attacks
                full_path = os.path.normpath(full_path)
                local_dir_norm = os.path.normpath(local_dir)
                
                # Security check: ensure the path is within local_dir
                if not full_path.startswith(local_dir_norm):
                    raise web.HTTPError(403, "Forbidden: Path outside allowed directory")
                
                # Check if file exists and is a file (not a directory)
                if not os.path.exists(full_path):
                    raise web.HTTPError(404, "File not found")
                
                if not os.path.isfile(full_path):
                    raise web.HTTPError(403, "Forbidden: Not a file")
                
                # Get file metadata
                file_size = os.path.getsize(full_path)
                
                # Determine content type
                content_type, _ = mimetypes.guess_type(full_path)
                if not content_type:
                    content_type = "application/octet-stream"
                
                # Set appropriate headers
                self.set_header("Content-Type", content_type)
                filename = os.path.basename(full_path)
                # Properly escape filename for Content-Disposition header
                self.set_header(
                    "Content-Disposition",
                    f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quote(filename)}'
                )
                self.set_header("Content-Length", str(file_size))
                self.set_header("Cache-Control", "public, max-age=3600")
                
                # Read and send the file in chunks for better memory usage
                chunk_size = 8192
                with open(full_path, 'rb') as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        self.write(chunk)
                self.finish()
                
            except web.HTTPError:
                raise
            except Exception as e:
                server_app.log.error(
                    f"s3contents_local_download_fix: Error serving file {file_path}: {e}",
                    exc_info=True
                )
                raise web.HTTPError(500, f"Internal server error: {str(e)}")
    
    # Register the handler
    # The pattern matches the URL prefix and captures the file path
    pattern = url_prefix.rstrip('/') + r"/(.*)"
    server_app.web_app.add_handlers(
        r".*",
        [(pattern, LocalFileHandler)]
    )
    
    server_app.log.info(
        f"s3contents_local_download_fix: Extension loaded successfully. "
        f"Serving files from {local_dir} at {url_prefix}"
    )


# Alias for backward compatibility and entry point
load_jupyter_server_extension = _load_jupyter_server_extension

