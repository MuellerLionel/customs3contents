"""
Jupyter extension to add static file handler for /files/local/ endpoint.
This allows file downloads to work properly with HybridContentsManager.
"""
import os
import mimetypes
from tornado.web import RequestHandler
from tornado import web

def _jupyter_server_extension_points():
    """Return a list of dictionaries with metadata about this extension."""
    return [{
        "module": "local_file_handler_extension"
    }]

def _jupyter_server_extension_paths():
    """Return paths for server extensions (legacy support)."""
    return [{
        "module": "local_file_handler_extension"
    }]

# Global variable to store the server app when it's available
_server_app = None

def _load_jupyter_server_extension(server_app):
    """Load the extension in Jupyter Server."""
    local_dir = "/home/jovyan/work"
    if os.path.exists(local_dir):
        # Create a custom handler that serves files from the local directory
        class LocalFileHandler(RequestHandler):
            # CSRF protection is enabled by default via RequestHandler
            # JupyterLab includes _xsrf token in download URLs, so this is secure
            
            def get(self, file_path):
                try:
                    # Construct the full file path
                    full_path = os.path.join(local_dir, file_path)
                    # Security check: ensure the path is within local_dir
                    full_path = os.path.normpath(full_path)
                    local_dir_norm = os.path.normpath(local_dir)
                    if not full_path.startswith(local_dir_norm):
                        raise web.HTTPError(403, "Forbidden")
                    
                    # Check if file exists
                    if not os.path.exists(full_path) or not os.path.isfile(full_path):
                        raise web.HTTPError(404, "File not found")
                    
                    # Get file size
                    file_size = os.path.getsize(full_path)
                    
                    # Determine content type
                    content_type, _ = mimetypes.guess_type(full_path)
                    if not content_type:
                        content_type = "application/octet-stream"
                    
                    # Set appropriate headers
                    self.set_header("Content-Type", content_type)
                    filename = os.path.basename(full_path)
                    self.set_header("Content-Disposition", f'attachment; filename="{filename}"')
                    self.set_header("Content-Length", str(file_size))
                    
                    # Enable caching for better performance
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
                    self.log.error(f"Error serving file {file_path}: {e}", exc_info=True)
                    raise web.HTTPError(500, f"Internal server error: {str(e)}")
        
        server_app.web_app.add_handlers(
            r".*",
            [
                (
                    r"/files/local/(.*)",
                    LocalFileHandler,
                ),
            ]
        )
        server_app.log.info("Local file handler extension loaded successfully")
        # Store the server app globally
        global _server_app
        _server_app = server_app

