import os
import mimetypes
import time
import threading
import logging
from datetime import datetime
from flask import send_from_directory, make_response, Response
from werkzeug.utils import secure_filename
import boto3
from botocore.exceptions import ClientError
from boto3.s3.transfer import TransferConfig
from utils import get_storage_info
import fsspec

logger = logging.getLogger(__name__)

class StorageProvider:
    def save(self, file_object, filename):
        raise NotImplementedError

    def exists(self, filename) -> bool:
        raise NotImplementedError

    def get_metadata(self, filename) -> dict:
        raise NotImplementedError

    def stream(self, filename, force_download=False, download_name=None):
        raise NotImplementedError

    def read(self, filename) -> bytes:
        raise NotImplementedError

    def get_stats(self) -> dict:
        raise NotImplementedError

    def delete(self, filename):
        raise NotImplementedError

    def get_file_object(self, filename):
        raise NotImplementedError

class LocalStorageProvider(StorageProvider):
    def __init__(self, folder):
        self.upload_folder = folder
        os.makedirs(self.upload_folder, exist_ok=True)

    def save(self, file_object, filename):
        safe_path = os.path.join(self.upload_folder, filename)
        logger.debug(f"Local storage: Saving file to {safe_path}")
        if hasattr(file_object, 'save'):
            file_object.save(safe_path)
        else:
            with open(safe_path, 'wb') as f:
                f.write(file_object.read())

        from extensions import meta_db
        stats = meta_db.get('_internal:local_stats')
        if stats is not None:
            file_size = os.path.getsize(safe_path)
            stats['total_files'] = stats.get('total_files', 0) + 1
            stats['storage_used_bytes'] = stats.get('storage_used_bytes', 0) + file_size
            meta_db.set('_internal:local_stats', stats)

    def exists(self, filename) -> bool:
        safe_path = secure_filename(filename)
        full_path = os.path.join(self.upload_folder, safe_path)
        return os.path.isfile(full_path)

    def get_metadata(self, filename) -> dict:
        safe_path = secure_filename(filename)
        full_path = os.path.join(self.upload_folder, safe_path)
        
        if not os.path.isfile(full_path):
            return None
            
        stat = os.stat(full_path)
        file_size = get_storage_info.get_pretty_bytes(stat.st_size)
        mime_type, _ = mimetypes.guess_type(safe_path)
        uploaded_at = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')

        return {
            'file_size': file_size,
            'mime_type': mime_type or 'application/octet-stream',
            'uploaded_at': uploaded_at,
        }

    def stream(self, filename, force_download=False, download_name=None):
        safe_path = secure_filename(filename)
        logger.debug(f"Local storage: Streaming file {safe_path} (force_download={force_download})")
        kwargs = {
            'as_attachment': force_download,
            'conditional': True
        }
        if force_download and download_name:
            kwargs['download_name'] = download_name
        return make_response(send_from_directory(
            self.upload_folder,
            safe_path,
            **kwargs
        ))

    def read(self, filename) -> bytes:
        safe_path = secure_filename(filename)
        full_path = os.path.join(self.upload_folder, safe_path)
        if not os.path.isfile(full_path):
            return None
        with open(full_path, 'rb') as f:
            return f.read()

    def delete(self, filename):
        safe_path = secure_filename(filename)
        full_path = os.path.join(self.upload_folder, safe_path)
        if os.path.isfile(full_path):
            logger.debug(f"Local storage: Deleting file {full_path}")
            file_size = os.path.getsize(full_path)
            os.remove(full_path)
            
            from extensions import meta_db
            stats = meta_db.get('_internal:local_stats')
            if stats is not None:
                stats['total_files'] = max(0, stats.get('total_files', 1) - 1)
                stats['storage_used_bytes'] = max(0, stats.get('storage_used_bytes', file_size) - file_size)
                meta_db.set('_internal:local_stats', stats)

    def get_stats(self) -> dict:
        if not os.path.exists(self.upload_folder):
            return {'total_files': 0, 'storage_used': '0 B'}
            
        from extensions import meta_db
        from utils.get_storage_info import get_pretty_bytes
        
        stats = meta_db.get('_internal:local_stats')
        
        if stats is None:
            total_size = 0
            total_files = 0
            with os.scandir(self.upload_folder) as it:
                for entry in it:
                    if entry.is_file(follow_symlinks=False):
                        total_size += entry.stat(follow_symlinks=False).st_size
                        total_files += 1
            stats = {
                'total_files': total_files,
                'storage_used_bytes': total_size
            }
            meta_db.set('_internal:local_stats', stats)
            
        return {
            'total_files': stats.get('total_files', 0),
            'storage_used': get_pretty_bytes(stats.get('storage_used_bytes', 0))
        }

    def get_file_object(self, filename):
        safe_path = secure_filename(filename)
        full_path = os.path.join(self.upload_folder, safe_path)
        if not os.path.isfile(full_path):
            return None
        return open(full_path, 'rb')

class S3StorageProvider(StorageProvider):
    def __init__(self, bucket, endpoint, access_key, secret_key, region):
        self.bucket = bucket
        self.s3 = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        self.fs = fsspec.filesystem(
            's3',
            key=access_key,
            secret=secret_key,
            client_kwargs={'endpoint_url': endpoint, 'region_name': region}
        )
        self._stats_lock = threading.Lock()

    def save(self, file_object, filename):
        logger.debug(f"S3 storage: Saving file {filename} to bucket {self.bucket}")
        mime_type, _ = mimetypes.guess_type(filename)
        extra_args = {}
        if mime_type:
            extra_args['ContentType'] = mime_type

        # s3 expects seek(0) before upload if we read the file
        file_object.seek(0, os.SEEK_END)
        file_size = file_object.tell()
        file_object.seek(0)
        self.s3.upload_fileobj(
            file_object,
            self.bucket,
            filename,
            ExtraArgs=extra_args,
            Config=TransferConfig(use_threads=False)
        )

        from extensions import meta_db
        stats = meta_db.get('_internal:s3_stats')
        if stats is not None:
            stats['total_files'] = stats.get('total_files', 0) + 1
            stats['storage_used_bytes'] = stats.get('storage_used_bytes', 0) + file_size
            meta_db.set('_internal:s3_stats', stats)

    def exists(self, filename) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=filename)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise

    def get_metadata(self, filename) -> dict:
        try:
            response = self.s3.head_object(Bucket=self.bucket, Key=filename)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            raise
        
        file_size = get_storage_info.get_pretty_bytes(response.get('ContentLength', 0))
        mime_type = response.get('ContentType', 'application/octet-stream')
        
        last_modified = response.get('LastModified')
        if last_modified:
            uploaded_at = last_modified.strftime('%Y-%m-%d %H:%M:%S')
        else:
            uploaded_at = "Unknown"

        return {
            'file_size': file_size,
            'mime_type': mime_type,
            'uploaded_at': uploaded_at,
        }

    def stream(self, filename, force_download=False, download_name=None):
        from flask import request
        logger.debug(f"S3 storage: Streaming file {filename} from bucket {self.bucket}")
        
        extra_args = {}
        range_header = request.headers.get('Range')
        if range_header:
            extra_args['Range'] = range_header

        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=filename, **extra_args)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                from werkzeug.exceptions import NotFound
                raise NotFound()
            raise
        
        def generate():
            try:
                for chunk in response['Body'].iter_chunks(chunk_size=4096):
                    yield chunk
            finally:
                response['Body'].close()

        status = 206 if 'ContentRange' in response else 200
        flask_response = Response(generate(), status=status, mimetype=response.get('ContentType', 'application/octet-stream'))
        
        dl_name = download_name if download_name else filename
        if force_download:
            flask_response.headers["Content-Disposition"] = f"attachment; filename={dl_name}"
        else:
            flask_response.headers["Content-Disposition"] = f"inline; filename={dl_name}"
            
        flask_response.headers["Content-Length"] = str(response.get('ContentLength', 0))
        
        if 'ContentRange' in response:
            flask_response.headers['Content-Range'] = response['ContentRange']
            
        flask_response.headers['Accept-Ranges'] = 'bytes'
            
        return flask_response

    def read(self, filename) -> bytes:
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=filename)
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise

    def delete(self, filename):
        logger.debug(f"S3 storage: Deleting file {filename} from bucket {self.bucket}")
        try:
            from extensions import meta_db
            stats = meta_db.get('_internal:s3_stats')
            file_size = 0
            if stats is not None:
                try:
                    response = self.s3.head_object(Bucket=self.bucket, Key=filename)
                    file_size = response.get('ContentLength', 0)
                except ClientError:
                    pass
            
            self.s3.delete_object(Bucket=self.bucket, Key=filename)
            
            if stats is not None and file_size > 0:
                stats['total_files'] = max(0, stats.get('total_files', 1) - 1)
                stats['storage_used_bytes'] = max(0, stats.get('storage_used_bytes', file_size) - file_size)
                meta_db.set('_internal:s3_stats', stats)
        except ClientError:
            pass

    def get_stats(self) -> dict:
        from extensions import meta_db
        stats = meta_db.get('_internal:s3_stats')
        last_update = meta_db.get('_internal:s3_stats_last_update') or 0
        
        if not stats or time.time() - last_update > 21600:
            def update_stats_task():
                total_size = 0
                total_files = 0
                paginator = self.s3.get_paginator('list_objects_v2')
                try:
                    for page in paginator.paginate(Bucket=self.bucket):
                        if 'Contents' in page:
                            for obj in page['Contents']:
                                total_files += 1
                                total_size += obj['Size']
                    
                    new_stats = {
                        'total_files': total_files,
                        'storage_used_bytes': total_size
                    }
                    meta_db.set('_internal:s3_stats', new_stats)
                    meta_db.set('_internal:s3_stats_last_update', time.time())
                except ClientError:
                    pass

            with self._stats_lock:
                last_update = meta_db.get('_internal:s3_stats_last_update') or 0
                if time.time() - last_update >= 21600 or not stats:
                    meta_db.set('_internal:s3_stats_last_update', time.time())
                    
                    thread = threading.Thread(target=update_stats_task)
                    thread.daemon = True
                    thread.start()

        if stats:
            from utils.get_storage_info import get_pretty_bytes
            return {
                'total_files': stats.get('total_files', 0),
                'storage_used': get_pretty_bytes(stats.get('storage_used_bytes', 0))
            }
                
        return {
            'total_files': 'Calculating...',
            'storage_used': 'Calculating...'
        }

    def get_file_object(self, filename):
        try:
            return self.fs.open(f"{self.bucket}/{filename}", "rb")
        except FileNotFoundError:
            return None
