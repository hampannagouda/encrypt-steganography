import os
import subprocess
import sys
import getpass

ENCRYPT_EXE = os.path.join("cpp", "encrypt.exe")
STEGO_SCRIPT = os.path.join("python", "stego.py")

def check_dependencies():
    if not os.path.exists(ENCRYPT_EXE):
        print(f"Error: {ENCRYPT_EXE} not found. Please compile it first.")
        sys.exit(1)
    if not os.path.exists(STEGO_SCRIPT):
        print(f"Error: {STEGO_SCRIPT} not found.")
        sys.exit(1)
    
    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)

def run_encrypt_tool(choice, input_file, output_file, password):
    """
    Runs the cpp/encrypt.exe tool interactively via subprocess.
    choice: '1' for Encrypt, '2' for Decrypt
    """
    try:
        # We pass the inputs directly to the executable's stdin
        process = subprocess.Popen(
            [ENCRYPT_EXE],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Build the input string to match what encrypt.cpp expects
        # 1. choice (1 or 2)
        # 2. input_file
        # 3. output_file
        # 4. password
        input_data = f"{choice}\n{input_file}\n{output_file}\n{password}\n"
        
        stdout, stderr = process.communicate(input=input_data)
        
        if process.returncode != 0:
            print("Error running encryption tool:")
            print(stderr)
            return False
            
        print(stdout)
        return True
    except Exception as e:
        print(f"Failed to run encryption tool: {e}")
        return False

def run_stego_tool(args):
    """
    Runs the python stego.py tool via subprocess.
    """
    try:
        cmd = [sys.executable, STEGO_SCRIPT] + args
        print(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Steganography tool failed with error code: {e.returncode}")
        return False
    except Exception as e:
        print(f"Failed to run steganography tool: {e}")
        return False

def hide_file_process():
    print("\n=== HIDE FILE PROCESS ===")
    input_file = input("Enter the path to the file you want to hide (e.g., input/dicom_original.dcm): ").strip()
    if not os.path.exists(input_file):
        print("Error: Input file does not exist.")
        return

    password = getpass.getpass("Enter a password to encrypt this file: ")
    encrypted_bin = os.path.join("output", "temp_encrypted.bin")
    
    print("\n[1/2] Encrypting file...")
    if not run_encrypt_tool('1', input_file, encrypted_bin, password):
        return
        
    cover_image = input("\nEnter the path to the cover image (TIFF format) (e.g., input/cover_float32.tif): ").strip()
    if not os.path.exists(cover_image):
        print("Error: Cover image does not exist.")
        return
        
    stego_out_dir = os.path.join("output", "stego_images")
    
    print("\n[2/2] Embedding encrypted file into cover image...")
    if run_stego_tool(['encode', encrypted_bin, cover_image, stego_out_dir]):
        print(f"\nSuccess! Your file has been hidden in images within the directory: {stego_out_dir}")
        
    # Clean up the intermediate encrypted binary
    if os.path.exists(encrypted_bin):
        os.remove(encrypted_bin)

def extract_file_process():
    print("\n=== EXTRACT FILE PROCESS ===")
    stego_dir = input("Enter the directory containing the hidden images (e.g., output/stego_images): ").strip()
    if not os.path.isdir(stego_dir):
        print("Error: Stego directory does not exist or is not a directory.")
        return
        
    extracted_bin = os.path.join("output", "temp_extracted.bin")
    
    print("\n[1/2] Extracting encrypted file from images...")
    if not run_stego_tool(['decode', stego_dir, extracted_bin]):
        return
        
    final_output = input("\nEnter the path for the final decrypted output file (e.g., output/recovered.dcm): ").strip()
    password = getpass.getpass("Enter the password to decrypt the file: ")
    
    print("\n[2/2] Decrypting file...")
    if run_encrypt_tool('2', extracted_bin, final_output, password):
        print(f"\nSuccess! Your recovered file is located at: {final_output}")
        
    # Clean up the intermediate extracted binary
    if os.path.exists(extracted_bin):
        os.remove(extracted_bin)

def main():
    check_dependencies()
    
    while True:
        print("\n" + "="*30)
        print("  SECURE STEGANOGRAPHY PIPELINE")
        print("="*30)
        print("1. Hide a File (Encrypt -> Embed)")
        print("2. Recover a File (Extract -> Decrypt)")
        print("3. Exit")
        
        choice = input("Enter your choice (1, 2, or 3): ").strip()
        
        if choice == '1':
            hide_file_process()
        elif choice == '2':
            extract_file_process()
        elif choice == '3':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please select 1, 2, or 3.")

if __name__ == "__main__":
    main()
