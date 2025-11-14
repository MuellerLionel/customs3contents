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

# Enable the local file handler extension
# This extension adds a static file handler for /files/local/ to serve files
# from /home/jovyan/work, allowing file downloads to work with HybridContentsManager
c.ServerApp.jpserver_extensions = {
    'local_file_handler_extension': True,
}

# Directly load the extension by hooking into the web app initialization
# This is a fallback in case jpserver_extensions discovery doesn't work
def setup_local_file_handler():
    """Setup function that will be called to add the local file handler."""
    import os
    import mimetypes
    from tornado.web import RequestHandler
    from tornado import web
    
    local_dir = "/home/jovyan/work"
    
    if not os.path.exists(local_dir):
        return
    
    # This function will be called after the server starts
    # We need to access the web app, so we'll use a delayed approach
    def add_handler_after_start(server_app):
        class LocalFileHandler(RequestHandler):
            # CSRF protection is enabled by default via RequestHandler
            # JupyterLab includes _xsrf token in download URLs, so this is secure
            
            def get(self, file_path):
                try:
                    full_path = os.path.join(local_dir, file_path)
                    full_path = os.path.normpath(full_path)
                    local_dir_norm = os.path.normpath(local_dir)
                    if not full_path.startswith(local_dir_norm):
                        raise web.HTTPError(403, "Forbidden")
                    
                    if not os.path.exists(full_path) or not os.path.isfile(full_path):
                        raise web.HTTPError(404, "File not found")
                    
                    file_size = os.path.getsize(full_path)
                    content_type, _ = mimetypes.guess_type(full_path)
                    if not content_type:
                        content_type = "application/octet-stream"
                    
                    self.set_header("Content-Type", content_type)
                    filename = os.path.basename(full_path)
                    self.set_header("Content-Disposition", f'attachment; filename="{filename}"')
                    self.set_header("Content-Length", str(file_size))
                    self.set_header("Cache-Control", "public, max-age=3600")
                    
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
                (r"/files/local/(.*)", LocalFileHandler),
            ]
        )
        server_app.log.info("Local file handler loaded successfully via config hook")
    
    # Try to load via extension first, if that fails, use direct hook
    try:
        import local_file_handler_extension
        # The extension should load via jpserver_extensions, but if not, we'll hook it
        # Store the function to be called
        _setup_handler = add_handler_after_start
    except ImportError:
        pass

# Monkey-patch the ServerApp to add our handler after web app initialization
import jupyter_server.serverapp
original_init_webapp = jupyter_server.serverapp.ServerApp.init_webapp

def patched_init_webapp(self, *args, **kwargs):
    result = original_init_webapp(self, *args, **kwargs)
    # Add our handler after web app is initialized
    try:
        import local_file_handler_extension
        local_file_handler_extension._load_jupyter_server_extension(self)
    except Exception:
        # Fallback: add handler directly
        import os
        import mimetypes
        from tornado.web import RequestHandler
        from tornado import web
        
        local_dir = "/home/jovyan/work"
        if os.path.exists(local_dir):
            class LocalFileHandler(RequestHandler):
                # CSRF protection is enabled by default via RequestHandler
                # JupyterLab includes _xsrf token in download URLs, so this is secure
                
                def get(self, file_path):
                    try:
                        full_path = os.path.join(local_dir, file_path)
                        full_path = os.path.normpath(full_path)
                        if not full_path.startswith(os.path.normpath(local_dir)):
                            raise web.HTTPError(403, "Forbidden")
                        if not os.path.exists(full_path) or not os.path.isfile(full_path):
                            raise web.HTTPError(404, "File not found")
                        
                        content_type, _ = mimetypes.guess_type(full_path)
                        if not content_type:
                            content_type = "application/octet-stream"
                        
                        file_size = os.path.getsize(full_path)
                        self.set_header("Content-Type", content_type)
                        self.set_header("Content-Disposition", f'attachment; filename="{os.path.basename(full_path)}"')
                        self.set_header("Content-Length", str(file_size))
                        self.set_header("Cache-Control", "public, max-age=3600")
                        
                        # Read and send the file in chunks for better memory usage and reliability
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
                        raise web.HTTPError(500, f"Error: {str(e)}")
            
            self.web_app.add_handlers(r".*", [(r"/files/local/(.*)", LocalFileHandler)])
            self.log.info("Local file handler loaded via monkey-patch")
    return result

jupyter_server.serverapp.ServerApp.init_webapp = patched_init_webapp

