import re

BLOCK_SHADE_RE = re.compile(r'([█▓▒░▄▀▌▐])')

def block_shade_filter(text):
    return BLOCK_SHADE_RE.sub(r'<span class="block">\1</span>', text)
