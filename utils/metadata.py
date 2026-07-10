import io
import os
import random
from PIL import Image, ExifTags

# make, model pairs applied together
REPLACEMENT_DEVICES = [
    ("Hasbro", "Lite-Brite Ultra"),
    ("Toaster", "Four-Slot Chrome"),
    ("Fridge", "Samsung IceMaker Pro"),
    ("NASA", "Hubble Space Telescope"),
    ("Nintendo", "Game Boy Camera"),
    ("Nintendo", "DSi"),
    ("GameCube", "Handle-Mounted Optical"),
    ("Raspberry Pi", "Camera Module (Secured with Duct Tape)"),
    ("CIA", "Classified Spy Satellite"),
    ("Epson", "Dot Matrix Printer"),
    ("Etch A Sketch", "Pro Max"),
    ("Unregistered HyperCam", "2"),
    ("The Sun", "Direct Retinal Burn"),
    ("Aperture Science", "Handheld Portal Device (Optical Module)"),
    ("DROP TABLE", "Images;--"),
    ("Gutenberg", "Printing Press Pro"),
    ("Cave Wall", "Charcoal v2"),
    ("Abacus", "RGB Edition"),
    ("MRI Machine", "Cross-Section Slice #42"),
    ("Casio", "Calculator Watch F-91W"),
    ("Ouroboros", "Self-Referential Lens"),
    ("Acme", "Image Capture Device"),
    ("Flock Safety", "Condor"),
    ("Omnicorp", "Citizen Compliance Dome"),
    ("Apex-Standard", "Loss-Prevention PTZ (Lethal Option Disabled)"),
    ("Bic", "4-Color Ballpoint Pen"),
]

# random GPS coordinates (latitude, longitude)
# positive means N/E, negative means S/W
REPLACEMENT_GPS = [
    (0.0, 0.0),
    (51.3892, 30.0994), # chernobyl nuclear reactor
    (11.55845, 92.24017), # north sentinel island
    (40.2526, 58.4398), # darvaza gas crater (also known as the gates of hell)
    (-24.4862, -46.6743), # snake island
    (-48.875, -123.3925), # point nemo
    (40.8037, -76.3414), # centralia, pennsylvania
    (78.2359, 15.4913), # svalbard global seed vault
    (57.5969, -13.6888), # rockall
    (-54.4232, 3.4206), # bouvet island
    (40.2588, -109.8837), # skinwalker ranch
    (45.3809, 12.3312), # poveglia island
    (38.9517, -77.1467), # cia headquarters
    (31.5958, -96.9881), # mount carmel center (waco siege)
    (-14.6975, -75.135), # nazca lines
    (51.1789, -1.8262), # stonehenge
    (40.6892, -74.0445), # inside the statue of liberty's torch
]

# random strings used for Software metadata
REPLACEMENT_SOFTWARE = [
    "Kid Pix",
    "Mario Paint",
    "Etch A Sketch Renderer",
    "3000 character ffmpeg command",
    "Enterprise-Grade Image Rasterization Microservice",
    "Macromedia Flash Player 8.0",
    "QuickTime 4 (Unregistered)",
    "Webpack (Compiled with 42 Warnings)",
    "Next.js Server-Side Rendered JPEG",
    "ImageMagick (StackOverflow Snippet #4392)",
    "Burp Suite Professional (Intercepted Payload)",
    "BeOS Graphics Library",
    "ReactOS Display Driver v0.4.14",
    "Notepad++ (Hex Editor Plugin)",
    "Dreamweaver CS6 Auto-Generated HTML",
    "Semi-Automated Bonesmashing Assistant v3.1",
    "Temple Run 2",
    "TollBooth-AutoCapture",
    "Palantir Gotham",
    "Microsoft Excel (compiled with VBA)",
    "mIRC v6.35",
]



TAG_TO_ID = {v: k for k, v in ExifTags.TAGS.items()}

def replace_image_metadata(file_stream, mime_type):
    if os.environ.get("REMOVE_IMAGE_METADATA", "false").lower() not in ("true", "1", "yes"):
        return file_stream

    if not mime_type or not mime_type.startswith('image/'):
        return file_stream

    # pillow doesn't support SVG, and EXIF isn't in SVG anyway
    if mime_type == 'image/svg+xml':
        return file_stream

    try:
        file_stream.seek(0)
        img = Image.open(file_stream)
        
        img_format = img.format
        if not img_format:
            raise ValueError("Unknown image format")
            
        new_exif = Image.Exif()
        
        make_val, model_val = random.choice(REPLACEMENT_DEVICES)
        new_exif[TAG_TO_ID["Make"]] = make_val
        new_exif[TAG_TO_ID["Model"]] = model_val
        
        new_exif[TAG_TO_ID["Software"]] = random.choice(REPLACEMENT_SOFTWARE)
            
        gps_ifd = new_exif.get_ifd(ExifTags.IFD.GPSInfo)
        lat, lon = random.choice(REPLACEMENT_GPS)
        
        gps_ifd[0] = (2, 2, 0, 0)  # GPSVersionID
        gps_ifd[1] = "N" if lat >= 0 else "S"
        gps_ifd[2] = abs(lat)
        gps_ifd[3] = "E" if lon >= 0 else "W"
        gps_ifd[4] = abs(lon)
            
        # keep original date tags
        original_exif = img.getexif()
        if TAG_TO_ID.get("DateTime") in original_exif:
            new_exif[TAG_TO_ID["DateTime"]] = original_exif[TAG_TO_ID["DateTime"]]
            
        # keep Orientation so images don't display sideways
        if TAG_TO_ID.get("Orientation") in original_exif:
            new_exif[TAG_TO_ID["Orientation"]] = original_exif[TAG_TO_ID["Orientation"]]
            
        original_exif_ifd = original_exif.get_ifd(ExifTags.IFD.Exif)
        new_exif_ifd = new_exif.get_ifd(ExifTags.IFD.Exif)
        
        date_tags = [
            "DateTimeOriginal", "DateTimeDigitized", 
            "OffsetTime", "OffsetTimeOriginal", "OffsetTimeDigitized",
            "SubSecTime", "SubSecTimeOriginal", "SubSecTimeDigitized"
        ]
        for tag_name in date_tags:
            tag_id = TAG_TO_ID.get(tag_name)
            if tag_id and tag_id in original_exif_ifd:
                new_exif_ifd[tag_id] = original_exif_ifd[tag_id]

            
        output = io.BytesIO()
        
        save_kwargs = {}
        
        if img_format in ['JPEG', 'TIFF', 'WEBP', 'PNG']:
            save_kwargs['exif'] = new_exif
            
        if img_format == 'JPEG':
            save_kwargs['quality'] = 'keep'  # prevent quality degradation
            
        # keep animation frames for GIFs and animated WebP
        if getattr(img, "is_animated", False):
            save_kwargs['save_all'] = True
            if 'duration' in img.info:
                save_kwargs['duration'] = img.info['duration']
            if 'loop' in img.info:
                save_kwargs['loop'] = img.info['loop']
                
        # keep ICC profile to prevent color washout
        if 'icc_profile' in img.info:
            save_kwargs['icc_profile'] = img.info['icc_profile']
            
        img.info = {}
        
        img.save(output, format=img_format, **save_kwargs)
        output.seek(0)
        
        # transfer attributes from werkzeug's FileStorage if needed
        if hasattr(file_stream, 'filename'):
            output.filename = file_stream.filename
        if hasattr(file_stream, 'name'):
            output.name = file_stream.name
        if hasattr(file_stream, 'headers'):
            output.headers = file_stream.headers
        if hasattr(file_stream, 'content_type'):
            output.content_type = file_stream.content_type
            
        return output
            
    except Exception as e:
        print(f"Error replacing image metadata: {e}")
        # if scrubbing fails, we should not upload the original
        raise ValueError(f"Failed to securely scrub image metadata: {e}")
