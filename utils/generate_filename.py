import os
import random
import string
import glob
import magic
import mimetypes

def generate_filename(buffer):
    file_id = generate_file_id()
    file_extension = get_extension(buffer)
    return f"{file_id}{file_extension}"

def generate_file_id(directory="uploads", length=5):
    os.makedirs(directory, exist_ok=True)
    
    chars = string.ascii_lowercase + string.digits
    
    while True:
        random_string = ''.join(random.choices(chars, k=length))
        
        search_pattern = os.path.join(directory, f"{random_string}.*")
        
        existing_files = glob.glob(search_pattern)
        
        if not existing_files:
            return random_string

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

