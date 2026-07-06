import os
import mimetypes
import json
import time
import threading
from datetime import datetime
from flask import send_from_directory, make_response, Response
from werkzeug.utils import secure_filename
import boto3
from botocore.exceptions import ClientError
from boto3.s3.transfer import TransferConfig
from utils import get_storage_info

class StorageProvider:
    def save(self, file_object, filename):
        raise NotImplementedError

    def exists(self, filename) -> bool:
        raise NotImplementedError

    def get_metadata(self, filename) -> dict:
        raise NotImplementedError

    def stream(self, filename, force_download=False):
        raise NotImplementedError

    def get_stats(self) -> dict:
        raise NotImplementedError

    def delete(self, filename):
        raise NotImplementedError

class LocalStorageProvider(StorageProvider):
    def __init__(self, folder):
        self.upload_folder = folder
        os.makedirs(self.upload_folder, exist_ok=True)
        self._cached_stats = None
        self._last_stats_update = 0

    def save(self, file_object, filename):
        safe_path = os.path.join(self.upload_folder, filename)
        file_object.save(safe_path)

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

    def stream(self, filename, force_download=False):
        safe_path = secure_filename(filename)
        return make_response(send_from_directory(
            self.upload_folder,
            safe_path,
            as_attachment=force_download,
            conditional=True
        ))

    def delete(self, filename):
        safe_path = secure_filename(filename)
        full_path = os.path.join(self.upload_folder, safe_path)
        if os.path.isfile(full_path):
            os.remove(full_path)

    def get_stats(self) -> dict:
        if not os.path.exists(self.upload_folder):
            return {'total_files': 0, 'storage_used': '0 B'}
            
        current_time = time.time()
        # cache for 5 minutes to prevent an I/O DOS attack
        if self._cached_stats is None or current_time - self._last_stats_update > 300:
            files_count = len(os.listdir(self.upload_folder))
            storage_size = get_storage_info.pretty_dir_size(self.upload_folder)
            self._cached_stats = {
                'total_files': files_count,
                'storage_used': storage_size
            }
            self._last_stats_update = current_time
            
        return self._cached_stats

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
        self._stats_file = "s3_stats.json"
        self._stats_lock = threading.Lock()

    def save(self, file_object, filename):
        mime_type, _ = mimetypes.guess_type(filename)
        extra_args = {}
        if mime_type:
            extra_args['ContentType'] = mime_type

        # s3 expects seek(0) before upload if we read the file
        file_object.seek(0)
        self.s3.upload_fileobj(
            file_object,
            self.bucket,
            filename,
            ExtraArgs=extra_args,
            Config=TransferConfig(use_threads=False)
        )

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

    def stream(self, filename, force_download=False):
        from flask import request
        
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
        
        if force_download:
            flask_response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        else:
            flask_response.headers["Content-Disposition"] = f"inline; filename={filename}"
            
        flask_response.headers["Content-Length"] = str(response.get('ContentLength', 0))
        
        if 'ContentRange' in response:
            flask_response.headers['Content-Range'] = response['ContentRange']
            
        flask_response.headers['Accept-Ranges'] = 'bytes'
            
        return flask_response

    def delete(self, filename):
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=filename)
        except ClientError:
            pass

    def get_stats(self) -> dict:
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
                
                storage_size = get_storage_info.get_pretty_bytes(total_size)
                stats = {
                    'total_files': total_files,
                    'storage_used': storage_size
                }
                temp_file = f"{self._stats_file}.{threading.get_ident()}.tmp"
                with open(temp_file, 'w') as f:
                    json.dump(stats, f)
                os.replace(temp_file, self._stats_file)
            except ClientError:
                pass

        file_exists = os.path.exists(self._stats_file)
        is_stale = True

        if file_exists:
            mtime = os.path.getmtime(self._stats_file)
            if time.time() - mtime < 300:  # 5 minutes
                is_stale = False

        if not file_exists or is_stale:
            with self._stats_lock:
                # double check inside the lock to avoid multiple threads running simultaneously
                mtime = os.path.getmtime(self._stats_file) if os.path.exists(self._stats_file) else 0
                if time.time() - mtime >= 300 or not os.path.exists(self._stats_file):
                    # touch the file to update mtime and stop other workers from starting threads
                    with open(self._stats_file, 'a'):
                        os.utime(self._stats_file, None)
                    
                    thread = threading.Thread(target=update_stats_task)
                    thread.daemon = True
                    thread.start()

        if file_exists:
            try:
                with open(self._stats_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
                
        return {
            'total_files': 'Calculating...',
            'storage_used': 'Calculating...'
        }
