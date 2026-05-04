To run the interactive project that asks you to select a process (Encrypt or Decrypt), you should run the pipeline.py file.

Here is the step-by-step to get it working:

First, compile the C++ code: Double-click the compile_encryption.bat file from your file explorer, OR run it in your terminal:

cmd
.\compile_encryption.bat
(Note: This requires you to have a C++ compiler like g++ installed. If you don't have it, the script will let you know).

Second, run the interactive pipeline: Run the Python script in your terminal:

cmd
python pipeline.py
When you run pipeline.py, it will present you with a menu to either Hide a File (which runs the C++ encryption, then Python steganography) or Recover a File (which runs Python steganography extraction, then C++ decryption).

# Hybrid Encryption and Steganography Pipeline

This plan outlines how to update the project to prompt the user for an option (encrypt or decrypt), and then orchestrate the execution of the C++ AES-GCM encryption code (`src/encryption/aes_gcm_encrypt.cpp`) and the Python steganography script (`src/steganography/stego.py`).

## User Review Required

> [!IMPORTANT]
> The C++ encryption code does not currently have a standalone CLI interface (it only contains the encryption functions). We will create a small wrapper file, but **you will need a C++ compiler** (like `g++` or Visual Studio's `cl`) to compile the new wrapper into an executable before the Python script can run it. 

## Open Questions

> [!WARNING]
> How are you currently compiling your C++ code on Windows? Do you use Visual Studio, MinGW (g++), or another IDE? I did not detect `g++` or `cl` in the default command prompt. I will provide a standard `g++` command, but please let me know if you use a different toolchain.

## Proposed Changes

### src/encryption

#### [NEW] [encrypt_cli.cpp](file:///c:/Users/GoudaHam/OneDrive%20-%20Unisys/Desktop/encrypt-steganography/src/encryption/encrypt_cli.cpp)
We will create a small C++ file with a `main()` function. This will act as a Command Line Interface (CLI) that takes arguments (encrypt/decrypt, input file, output file, password) and calls the functions from `aes_gcm_encrypt.cpp`.

### Project Root

#### [MODIFY] [pipeline.py](file:///c:/Users/GoudaHam/OneDrive%20-%20Unisys/Desktop/encrypt-steganography/pipeline.py)
We will update the main pipeline script to:
1. Ask the user whether they want to **Encrypt & Hide** or **Extract & Decrypt**.
2. Change the tool paths to use `src/encryption/encrypt_cli.exe` and `src/steganography/stego.py`.
3. Update `run_encrypt_tool` to pass arguments via the command line instead of interactively, since our new `encrypt_cli.cpp` will be designed to accept arguments directly.

#### [NEW] [compile_encryption.bat](file:///c:/Users/GoudaHam/OneDrive%20-%20Unisys/Desktop/encrypt-steganography/compile_encryption.bat)
A small helper batch script to easily compile the C++ encryption executable using `g++` (if available in your environment).

## Verification Plan

### Automated/Manual Tests
1. Run `compile_encryption.bat` to ensure the executable is built.
2. Run `python pipeline.py`.
3. Select "1" (Hide a File). Provide an input file, a cover image, and a password. Verify the output is generated.
4. Select "2" (Recover a File). Provide the stego image directory, output file path, and password. Verify the file is correctly decrypted.
