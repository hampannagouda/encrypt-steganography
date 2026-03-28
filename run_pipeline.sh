#!/bin/bash

set -e  # stop if any error

echo "🔹 Step 1: Compiling C++..."
g++ cpp/encrypt.cpp -o encrypt -lssl -lcrypto

echo "🔹 Step 2: Encrypting file..."
./encrypt ./encrypt encrypt input/dicom_original.dcm output/encrypted.bin mypassword

echo "🔹 Step 3: Encoding (Steganography)..."
python3 python/stego.py encode \
    output/encrypted.bin \
    input/cover_image.tif \
    output/stego_image.png

echo "🔹 Step 4: Decoding..."
python3 python/stego.py decode \
    output/stego_image.png \
    output/extracted.bin

echo "🔹 Step 5: Verifying..."
python3 python/stego.py verify \
    output/encrypted.bin \
    output/extracted.bin

echo "✅ PIPELINE COMPLETED SUCCESSFULLY"