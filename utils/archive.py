import libarchive

# Zip bomb protection limits
MAX_ARCHIVE_FILES = 5000
MAX_UNCOMPRESSED_SIZE = 1 * 1024 * 1024 * 1024 # 1 GB

def get_archive_contents(file_obj):
    """
    Reads an archive and returns a list of dictionaries representing its contents.
    Raises ValueError or Exception if parsing fails.
    """
    archive_contents = []
    total_size = 0
    file_count = 0
    
    with libarchive.seekable_stream_reader(file_obj) as archive:
        for entry in archive:
            file_count += 1
            if file_count > MAX_ARCHIVE_FILES:
                raise ValueError("Archive contains too many files (zip bomb protection).")
            
            total_size += entry.size
            if total_size > MAX_UNCOMPRESSED_SIZE:
                raise ValueError("Archive uncompressed size is too large (zip bomb protection).")
                
            archive_contents.append({
                'name': entry.pathname,
                'size': entry.size,
                'is_dir': entry.isdir
            })
    return archive_contents

def stream_archive_file(file_obj, inner_path):
    """
    Generator to stream a specific file from an archive.
    """
    try:
        with libarchive.seekable_stream_reader(file_obj) as archive:
            file_count = 0
            for entry in archive:
                file_count += 1
                if file_count > MAX_ARCHIVE_FILES:
                    break  # Prevent iterating over too many files (DoS protection)
                    
                if entry.pathname == inner_path:
                    if entry.isdir:
                        break
                    
                    if entry.size > MAX_UNCOMPRESSED_SIZE:
                        break  # Prevent extracting massive files (DoS protection)
                        
                    for block in entry.get_blocks():
                        yield block
                    break
    finally:
        file_obj.close()
