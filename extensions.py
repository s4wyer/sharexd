import os
from pathlib import Path
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from utils.storage import LocalStorageProvider, S3StorageProvider
from utils.meta_db import MetaDB
from config import Config

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["2000 per minute"],
    storage_uri="memory://"
)

if Config.STORAGE_BACKEND == "s3":
    storage = S3StorageProvider(
        bucket=Config.S3_BUCKET_NAME,
        endpoint=Config.S3_ENDPOINT_URL,
        access_key=Config.S3_ACCESS_KEY_ID,
        secret_key=Config.S3_SECRET_ACCESS_KEY,
        region=Config.S3_REGION
    )
else:
    Path(Config.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
    storage = LocalStorageProvider(folder=Config.UPLOAD_FOLDER)

meta_db = MetaDB(path="meta.lmdb")
