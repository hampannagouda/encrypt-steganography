# Pipeline Web Frontend Integration

This plan details the creation of a full-stack web application to provide a simple, yet beautiful graphical user interface (Frontend) for the encryption and steganography pipeline. 

## Proposed Changes

### Backend Integration
#### [NEW] app.py
A modern Python web server using the `Flask` framework.
- Initializes file upload boundaries and temp directories for processing.
- Exposes robust API endpoints (`/api/hide` and `/api/extract`) that handle file uploads, execute the underlying `subprocess` tools (C++ executable and Python [stego.py](file:///c:/Users/80732/Desktop/project/python/stego.py) script), and stream the resulting files back to the user.

### Web Frontend Design
#### [NEW] templates/index.html
A beautifully designed, single-page application structure.
- Adheres to premium modern web design aesthetics (Glassmorphism, dark-mode styling, smooth transitions).
- Splits the view into two interactive tabs: **"Hide a File"** and **"Recover a File"**.

#### [NEW] static/css/style.css
- Custom Vanilla CSS avoiding external frameworks.
- Uses dynamic backgrounds, soft drop shadows, and modern typography (e.g., `Inter` or `Roboto` from Google Fonts).
- Includes micro-animations for buttons, drag-and-drop boxes, and loading states.

#### [NEW] static/js/main.js
- Frontend logic managing states (Uploading, Processing, Success, Error).
- Uses Fetch API to seamlessly handle multiform data uploads.
- Validates inputs gracefully.

## Verification Plan

### Manual Verification
1. Install Flask via `pip install flask`.
2. Start the web server by running `python app.py`.
3. Open a browser to `http://127.0.0.1:5000/`.
4. Run the "Hide File" process using a test file and test cover image. Ensure the server zips and downloads the resulting directory.
5. Run the "Recover File" process by uploading the steganography file and extracting the original secret.
