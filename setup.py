"""
Setup script for s3contents-local-download-fix extension.

This package provides a Jupyter Server extension that fixes file download
issues when using HybridContentsManager with local file storage.
"""
from setuptools import setup, find_packages

setup(
    name="s3contents-local-download-fix",
    version="1.0.0",
    description="Fix file downloads for local files in HybridContentsManager setups",
    long_description=open("README.md").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="",
    author_email="",
    url="https://github.com/yourusername/s3contents-local-download-fix",
    py_modules=["s3contents_local_download_fix"],
    package_data={},
    install_requires=[
        "jupyter-server>=1.0.0",
        "tornado>=6.0",
    ],
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    entry_points={
        "jupyter_server.server_extensions": [
            "s3contents_local_download_fix = s3contents_local_download_fix:load_jupyter_server_extension",
        ],
    },
)

