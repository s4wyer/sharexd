import os
import random
import string
import glob
import magic
import mimetypes

mimetypes.add_type('audio/x-m4a', '.m4a')

def generate_filename(buffer, check_exists_func=None):
    file_extension = get_extension(buffer)
    
    chars = string.ascii_lowercase + string.digits
    length = 5
    
    while True:
        file_id = ''.join(random.choices(chars, k=length))
        filename = f"{file_id}{file_extension}"
        
        if check_exists_func:
            if not check_exists_func(filename):
                return filename
        else:
            search_pattern = os.path.join("uploads", f"{file_id}.*")
            if not glob.glob(search_pattern):
                return filename

def get_extension(buffer):
    mime_type = magic.from_buffer(buffer, mime=True)

    if mime_type == '':
        mime_type = 'application/octet-stream'

    file_extension = None

    # force non-standard text types to be recognized as plain text
    if mime_type.startswith('text/x-'):
        # custom handler for python scripts to maintain the extension
        # must also be handled in main.py so it returns as text/plain
        if mime_type == 'text/x-script.python':
            file_extension = '.py'
        else:
            mime_type = 'text/plain'

    if file_extension is None:
        file_extension = mimetypes.guess_extension(mime_type)

    return file_extension or '.bin'

