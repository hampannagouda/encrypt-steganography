#ifndef AES_GCM_ENCRYPT_H
#define AES_GCM_ENCRYPT_H

#include <string>

/*
 * Encrypts a file using AES-256-GCM.
 *
 * @param inPath   Path to the input file (image / binary)
 * @param outPath  Path where encrypted file will be written
 * @param password User-provided password for key derivation
 *
 * Throws std::runtime_error on failure.
 */
void encryptFile(const std::string& inPath,
                 const std::string& outPath,
                 const std::string& password);

/*
 * Decrypts a file encrypted using AES-256-GCM.
 *
 * @param inPath   Path to encrypted file
 * @param outPath  Path where decrypted file will be written
 * @param password Password used during encryption
 *
 * Throws std::runtime_error if authentication fails or on error.
 */
void decryptFile(const std::string& inPath,
                 const std::string& outPath,
                 const std::string& password);

#endif // AES_GCM_ENCRYPT_H
