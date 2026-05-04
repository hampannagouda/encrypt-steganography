#include <iostream>
#include <string>
#include <exception>
#include "aes_gcm_encrypt.h"

void printUsage(const char* progName) {
    std::cerr << "Usage:\n"
              << "  " << progName << " encrypt <input_file> <output_file> <password>\n"
              << "  " << progName << " decrypt <input_file> <output_file> <password>\n";
}

int main(int argc, char* argv[]) {
    if (argc != 5) {
        printUsage(argv[0]);
        return 1;
    }

    std::string mode = argv[1];
    std::string inputFile = argv[2];
    std::string outputFile = argv[3];
    std::string password = argv[4];

    try {
        if (mode == "encrypt") {
            std::cout << "Encrypting " << inputFile << " to " << outputFile << "...\n";
            encryptFile(inputFile, outputFile, password);
            std::cout << "Encryption successful.\n";
        } else if (mode == "decrypt") {
            std::cout << "Decrypting " << inputFile << " to " << outputFile << "...\n";
            decryptFile(inputFile, outputFile, password);
            std::cout << "Decryption successful.\n";
        } else {
            std::cerr << "Error: Unknown mode '" << mode << "'\n";
            printUsage(argv[0]);
            return 1;
        }
    } catch (const std::exception& e) {
        std::cerr << "Error during " << mode << ": " << e.what() << "\n";
        return 1;
    }

    return 0;
}
