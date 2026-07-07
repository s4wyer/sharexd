# Viewers
  - [ ] Archives
  - [ ] Markdown (no html)
  - [ ] PDFs (pdf.js)
  - [ ] OBJ/STL files (three.js)
  - [ ] CSV (convert to an html table)
  - [ ] Show metadata for media files
  - [-] Text
    - [ ] Syntax highlighting
  - [x] Unknown files

# Security
  - [ ] Option to disallow executables
  - [x] Implement upload tokens
    - [x] Multiple tokens for different users
    - [x] Single token
  - [x] Rate-limiting with flask-limiter
  - [x] Deliver HTML as text/plain

# Configuration
  - [ ] Customizable filename length
  - [ ] Gfycat style filenames
  - [x] File size limit

# Maintainability
  - [ ] Debug logs
  - [x] Split each route into different files

# Design
  - [ ] Add server uptime to the index page
  - [ ] Running `curl` should return the same information as displayed in the <pre> tag instead of returning html
  - [ ] Audio player waveform

# Functionality
  - [ ] Pass an X-Compress: true header to compress images to webp, audio to opus, and video to vp9 (webm)
  - [ ] Chunking for faster uploads
  - [ ] Image info (width, height)
  - [ ] Add a file hash to the beginning of the file name to de-dupe and display the hash on the view page
  - [ ] /qr route to generate QR codes. It should work with curl and also generate QR codes using block characters
  - [ ] /read route to use pytesseract to run OCR on an image
  - [ ] /gif route to convert videos to gifs. Optionally pass a timestamp with a query parameter to trim the video
  - [ ] Pipe text to sxd and have it treated like a plain text upload
  - [x] Strip metadata
  - [x] Deletion URLs
  - [x] Write a shell script to upload to sharexd
  - [x] S3 integration

# Fun
  - [ ] /ascii route to generate an ascii representation of the image
  - [ ] /vhs route with WebGL filters for the video player
  - [ ] /screw to chop and screw an audio file
  - [ ] /nightcore to pitch up and speed up by 1.25x
  - [ ] /dis for python files to use the dis built in and show raw bytecode for a python file
  - [ ] Send the X-Vampire header to only allow the uploaded file to be viewed between 9 P.M and 5 A.M
  - [ ] /verify for captchas
    - [ ] Different shades of off white. “Select every image containing a wall painted in eggshell white. do not select satin white.”
    - [ ] "To prove you are human, drag the slider to exactly 42.0000%."
    - [ ] Complicated regex, must submit a string that matches
    - [ ] You must use SQL injection to bypass the captcha
    - [ ] Click the button in exactly 2.718 seconds, and if you fail, reject the user for "being out of rhythm"
    - [ ] Find the syntax error (easy to implement with ast.parse)
  - [x] Replace metadata with other values (like setting the camera to a Nintendo DSi and the coordinates to the Marianna Trench)  
