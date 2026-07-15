import lmdb
import json
import threading
import time
import os
import shutil
import tempfile
import uuid
import logging
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

class MetaDB:
    def __init__(self, path="meta.lmdb"):
        self.path = path
        self.env = None
        self.db = None
        self._lock = threading.Lock()

    def _init_db(self):
        if self.env is None:
            with self._lock:
                if self.env is None:
                    # 1gb map_size is plenty, but like just in case we dynamically resize if it 
                    # ever goes past that 
                    # sync=False, metasync=False, and writemap=True improve performance
                    self.env = lmdb.open(
                        self.path,
                        map_size=1024*1024*1024,
                        max_dbs=1,
                        sync=False,
                        metasync=False,
                        writemap=True,
                        max_readers=1024
                    )
                    self.db = self.env.open_db(b'metadata')
                    self._start_backup_thread()

    def get(self, filename: str) -> dict:
        self._init_db()
        with self.env.begin(db=self.db) as txn:
            data = txn.get(filename.encode('utf-8'))
            if data:
                return json.loads(data.decode('utf-8'))
        return None

    def set(self, filename: str, metadata: dict):
        self._init_db()
        try:
            self._do_set(filename, metadata)
        except lmdb.MapFullError:
            # double the map_size if it gets full
            new_size = self.env.info()['map_size'] * 2
            logger.debug(f"MetaDB: LMDB map full, resizing to {new_size} bytes")
            self.env.set_mapsize(new_size)
            self._do_set(filename, metadata)

    def _do_set(self, filename: str, metadata: dict):
        logger.debug(f"MetaDB: Setting metadata for {filename}")
        with self.env.begin(db=self.db, write=True) as txn:
            txn.put(
                filename.encode('utf-8'),
                json.dumps(metadata).encode('utf-8')
            )

    def delete(self, filename: str):
        self._init_db()
        logger.debug(f"MetaDB: Deleting metadata for {filename}")
        with self.env.begin(db=self.db, write=True) as txn:
            txn.delete(filename.encode('utf-8'))

    def _start_backup_thread(self):
        if Config.STORAGE_BACKEND != "s3":
            return
            
        def backup_loop():
            from extensions import storage
            while True:
                try:
                    self._perform_s3_backup(storage)
                except Exception as e:
                    logger.debug(f"S3 backup failed: {e}")
                    print(f"S3 backup failed: {e}")
                time.sleep(86400) # sleep 24 hours

        # start the backup loop immediately so it uploads on startup 
        thread = threading.Thread(target=backup_loop, daemon=True)
        thread.start()

    def _perform_s3_backup(self, storage):
        today = datetime.now().strftime("%Y-%m-%d")
        s3_key = f"BACKUP-{today}_meta.mdb"
        lock_key = b'_internal:backup_lock'
        
        with self.env.begin(db=self.db) as txn:
            last_backup = txn.get(b'_internal:last_backup_date')
            if last_backup == today.encode('utf-8'):
                return

        # get a backup lock for today to prevent workers from backing up at the same time
        with self.env.begin(db=self.db, write=True) as txn:
            current_lock = txn.get(lock_key)
            if current_lock == today.encode('utf-8'):
                return
            txn.put(lock_key, today.encode('utf-8'))
        
        try:
            if storage.exists(s3_key):
                # write last backup date so we don't check S3 again today
                with self.env.begin(db=self.db, write=True) as txn:
                    txn.put(b'_internal:last_backup_date', today.encode('utf-8'))
                self._prune_old_backups(storage)
                return
                
            backup_dir = os.path.join(tempfile.gettempdir(), f"sharexd_meta_backup_{uuid.uuid4().hex}")
            logger.debug(f"MetaDB: Starting S3 backup for today ({today}) to {s3_key}")
            os.makedirs(backup_dir, exist_ok=True)
            try:
                self.env.copy(backup_dir, compact=True)
                data_file = os.path.join(backup_dir, "data.mdb")
                
                if os.path.exists(data_file):
                    with open(data_file, 'rb') as f:
                        storage.save(f, s3_key)
                        logger.debug(f"MetaDB: Successfully uploaded S3 backup {s3_key}")
            finally:
                if os.path.exists(backup_dir):
                    shutil.rmtree(backup_dir)
                    
            with self.env.begin(db=self.db, write=True) as txn:
                txn.put(b'_internal:last_backup_date', today.encode('utf-8'))
                
            self._prune_old_backups(storage)
        except Exception:
            with self.env.begin(db=self.db, write=True) as txn:
                txn.delete(lock_key)
            raise

    def _prune_old_backups(self, storage):
        if not hasattr(storage, 's3'):
            return
            
        try:
            paginator = storage.s3.get_paginator('list_objects_v2')
            backups = []
            for page in paginator.paginate(Bucket=storage.bucket, Prefix="BACKUP-"):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        backups.append(obj)
            
            backups.sort(key=lambda x: x['LastModified'])
            
            if len(backups) > 7:
                for obj in backups[:-7]:
                    logger.debug(f"MetaDB: Pruning old S3 backup {obj['Key']}")
                    storage.delete(obj['Key'])
        except Exception as e:
            logger.debug(f"Failed to prune old backups: {e}")
            print(f"Failed to prune old backups: {e}")
