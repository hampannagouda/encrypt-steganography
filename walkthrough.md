# Secure Steganography Pipeline Automation

I have successfully created an automated, interactive Python script to orchestrate the encryption and steganography processes into two seamless user workflows exactly as requested.

## What Was Done

- Created a new master script: [pipeline.py](file:///c:/Users/80732/Desktop/project/pipeline.py)
- Integrated the compiled C++ executable [cpp/encrypt.exe](file:///c:/Users/80732/Desktop/project/cpp/encrypt.exe) with [python/stego.py](file:///c:/Users/80732/Desktop/project/python/stego.py) via `subprocess`.
- The script uses automated interaction to provide passwords and choices directly to the C++ executable's standard input.

## How to used

python -m venv venv
.\venv\bin\Activate.ps1
py -m pip install numpy opencv-python torch torchvision pillow tifffile scikit-image
py pipeline.py

Run the script from your terminal:
```bash
python pipeline.py
```

It will present you with a clean menu:
```text
==============================
  SECURE STEGANOGRAPHY PIPELINE
==============================
1. Hide a File (Encrypt -> Embed)
2. Recover a File (Extract -> Decrypt)
3. Exit
```

### 1. Hiding a File
Select `1`. The script will ask you sequentially for:
1. The path to the file you wish to hide (e.g. [input/dicom_original.dcm](file:///c:/Users/80732/Desktop/project/input/dicom_original.dcm))
2. The password to encrypt it
3. The path to the cover image (e.g. [input/cover_float32.tif](file:///c:/Users/80732/Desktop/project/input/cover_float32.tif))

Behind the scenes, it encrypts the file securely and then embeds it into your cover image inside the `output/stego_images/` directory.

### 2. Extracting a File
Select `2`. The script will ask you for:
1. The directory containing the steganography images (e.g. `output/stego_images`)
2. The final destination to save the recovered file
3. The password to decrypt it

Behind the scenes, it decodes the intermediate binary representation from the TIFF file and decrypts it back to your original format using the password you provide.
