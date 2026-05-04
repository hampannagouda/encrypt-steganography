#!/bin/bash

set -e  # stop if any error

echo "🔹 Step 1: Compiling C++..."
g++ -std=c++17 src/encryption/encrypt_cli.cpp src/encryption/aes_gcm_encrypt.cpp -o src/encryption/encrypt_cli -lcrypto

echo "🔹 Step 2: Encrypting file..."
./src/encryption/encrypt_cli encrypt input/dicom_original.dcm output/encrypted.bin mypassword

echo "🔹 Step 3: Encoding (Steganography)..."
python3 src/steganography/stego.py encode \
    output/encrypted.bin \
    input/cover_image.tif \
    output/stego_image.png

echo "🔹 Step 4: Decoding..."
python3 src/steganography/stego.py decode \
    output/stego_image.png \
    output/extracted.bin

echo "🔹 Step 5: Verifying..."
python3 src/steganography/stego.py verify \
    output/encrypted.bin \
    output/extracted.bin

echo "✅ PIPELINE COMPLETED SUCCESSFULLY"