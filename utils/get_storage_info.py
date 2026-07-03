import os

def get_flat_dir_size(path):
    total_size = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file(follow_symlinks=False):
                total_size += entry.stat(follow_symlinks=False).st_size
                
    return total_size

def get_pretty_bytes(size):
    units = ['Bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
    
    if size == 0:
        return "0 Bytes"
    
    for unit in units:
        if size < 1024.0:
            break
        if unit != units[-1]: 
            size /= 1024.0
            
    
    if unit == 'Bytes':
        return f"{int(size)} {unit}"
    else:
        return f"{size:.1f} {unit}"

def pretty_dir_size(path):
    size = get_flat_dir_size(path)
    return get_pretty_bytes(size)
    
