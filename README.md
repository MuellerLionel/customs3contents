# JupyterLab with S3 Contents Manager

This setup provides a complete Docker Compose ecosystem with:
- **JupyterLab**: Interactive development environment
- **MinIO**: S3-compatible object storage server
- **s3contents**: Jupyter contents manager for S3
- **hybridcontents**: Allows access to both S3 and local files

## Prerequisites

- Docker
- Docker Compose

## Quick Start

1. **Start all services:**
   ```bash
   docker-compose up -d
   ```

2. **Access the services:**
   - **JupyterLab**: http://localhost:8888
   - **MinIO Console**: http://localhost:9001
     - Username: `minioadmin`
     - Password: `minioadmin123`

3. **Stop all services:**
   ```bash
   docker-compose down
   ```

4. **Stop and remove volumes (clean slate):**
   ```bash
   docker-compose down -v
   ```

## Configuration

### MinIO S3 Server

- **Access Key ID**: `minioadmin`
- **Secret Access Key**: `minioadmin123`
- **Endpoint**: `http://minio:9000` (internal) or `http://localhost:9000` (external)
- **Bucket**: `jupyter-notebooks` (created automatically)

### JupyterLab Configuration

The JupyterLab is configured to use `HybridContentsManager` which provides:

1. **S3 Storage** (root directory): All notebooks and files saved in the root will be stored in S3
2. **Local Storage** (`/local` directory): Files in the `/local` path will be stored locally

### File Structure

- `docker-compose.yml`: Main orchestration file
- `Dockerfile`: Custom JupyterLab image with s3contents
- `jupyter_config/jupyter_notebook_config.py`: Jupyter configuration
- `notebooks/`: Local directory for notebooks (mounted as volume)

## Usage

### Accessing S3 Files

When you open JupyterLab, files in the root directory are stored in S3. You can:
- Create new notebooks (they'll be saved to S3)
- Upload files (they'll be stored in S3)
- Organize files in folders (folders are created in S3)

### Accessing Local Files

To access local files, navigate to the `/local` directory in JupyterLab's file browser. Files here are stored on the local filesystem.

### MinIO Console

You can manage your S3 buckets and files through the MinIO web console:
1. Go to http://localhost:9001
2. Login with `minioadmin` / `minioadmin123`
3. Browse the `jupyter-notebooks` bucket to see your files

## Customization

### Change MinIO Credentials

Edit `docker-compose.yml`:
```yaml
environment:
  MINIO_ROOT_USER: your-username
  MINIO_ROOT_PASSWORD: your-password
```

Then update `jupyter_config/jupyter_notebook_config.py`:
```python
"": {
    "access_key_id": "your-username",
    "secret_access_key": "your-password",
    ...
}
```

### Change S3 Bucket Name

1. Update the bucket name in `docker-compose.yml` (minio-setup service)
2. Update the bucket name in `jupyter_config/jupyter_notebook_config.py`

### Change JupyterLab Port

Edit `docker-compose.yml`:
```yaml
ports:
  - "YOUR_PORT:8888"
```

## Troubleshooting

### Check service logs:
```bash
docker-compose logs jupyterlab
docker-compose logs minio
```

### Restart a specific service:
```bash
docker-compose restart jupyterlab
```

### Access JupyterLab container shell:
```bash
docker exec -it jupyterlab-s3 bash
```

## Architecture

```
┌─────────────────┐
│   JupyterLab    │
│   (Port 8888)   │
└────────┬────────┘
         │
         │ Uses s3contents + hybridcontents
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
│ MinIO │ │  Files  │
└───────┘ └─────────┘
```

## License

This setup is provided as-is for development and testing purposes.

