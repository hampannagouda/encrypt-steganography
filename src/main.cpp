#include <iostream>
#include <string>

// encryption
#include "encryption/aes_gcm_encrypt.h"

// steganography
#include "steganography/lsb_encoder.h"

void printUsage(const std::string& prog) {
    std::cout << "\nUsage:\n";
    std::cout << prog << " encrypt-hide <input_file> <cover_image> <stego_image> <password>\n";
    std::cout << prog << " extract-decrypt <stego_image> <output_file> <password>\n\n";
}

int main(int argc, char* argv[]) {

    if (argc < 2) {
        printUsage(argv[0]);
        return 1;
    }

    std::string mode = argv[1];

    try {
        // ================= ENCRYPT + HIDE =================
        if (mode == "encrypt-hide") {

            if (argc != 6) {
                printUsage(argv[0]);
                return 1;
            }

            std::string inputFile   = argv[2];
            std::string coverImage  = argv[3];
            std::string stegoImage  = argv[4];
            std::string password    = argv[5];

            std::string encryptedFile = "output/encrypted.bin";

            std::cout << "[1] Encrypting input file...\n";
            encryptFile(inputFile, encryptedFile, password);

            std::cout << "[2] Embedding encrypted data into image...\n";
            embedDataInImage(coverImage, encryptedFile, stegoImage);

            std::cout << "\n✔ Encryption + Steganography completed successfully\n";
        }

        // ================= EXTRACT + DECRYPT =================
        else if (mode == "extract-decrypt") {

            if (argc != 5) {
                printUsage(argv[0]);
                return 1;
            }

            std::string stegoImage = argv[2];
            std::string outputFile = argv[3];
            std::string password   = argv[4];

            std::string extractedFile = "output/extracted.bin";

            std::cout << "[1] Extracting encrypted data from image...\n";
            extractDataFromImage(stegoImage, extractedFile);

            std::cout << "[2] Decrypting extracted data...\n";
            decryptFile(extractedFile, outputFile, password);

            std::cout << "\n✔ Extraction + Decryption completed successfully\n";
        }

        else {
            printUsage(argv[0]);
            return 1;
        }

    } catch (const std::exception& e) {
        std::cerr << "\n❌ Error: " << e.what() << "\n";
        return 1;
    }

    return 0;
}
