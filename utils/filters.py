import re

def block_shade_filter(text):
    return re.sub(r'([█▓▒░▄▀▌▐])', r'<span class="block">\1</span>', text)
