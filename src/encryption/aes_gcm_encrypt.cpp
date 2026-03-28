// main.cpp
// Build: g++ -std=c++17 main.cpp -o imagecrypto -lcrypto

#include <iostream>
#include <vector>
#include <fstream>
#include <string>
#include <cstring>
#include <array>
#include <stdexcept>
#include <chrono>

#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/err.h>
#include <openssl/sha.h>
#include <openssl/crypto.h>

using byte = unsigned char;

static const size_t SALT_LEN = 16;
static const size_t NONCE_LEN = 12;
static const size_t TAG_LEN = 16;
static const size_t KEY_LEN = 32;
static const int PBKDF2_ITERS = 200000;
static const size_t CHUNK_SIZE = 8192 * 8192; // 8MB

static const std::array<byte,8> MAGIC = {'I','M','G','C','E','N','C','1'};
static const byte VERSION = 1;

void handleOpenSSLErrors() {
    ERR_print_errors_fp(stderr);
    throw std::runtime_error("OpenSSL error");
}

double getFileSizeMB(const std::string& path) {
    std::ifstream f(path, std::ios::binary | std::ios::ate);
    if (!f) throw std::runtime_error("Cannot open file for size");
    return static_cast<double>(f.tellg()) / (1024.0 * 1024.0);
}

void deriveKeyFromPassword(const std::string &password,
                           const std::vector<byte> &salt,
                           std::vector<byte> &key) {
    key.resize(KEY_LEN);
    if (!PKCS5_PBKDF2_HMAC(password.c_str(), password.size(),
                           salt.data(), salt.size(),
                           PBKDF2_ITERS,
                           EVP_sha256(),
                           key.size(), key.data()))
        handleOpenSSLErrors();
}

void secureClear(std::vector<byte>& v) {
    if (!v.empty()) OPENSSL_cleanse(v.data(), v.size());
    v.clear();
}

// ================= ENCRYPT =================
void encryptFile(const std::string &inPath,
                 const std::string &outPath,
                 const std::string &password) {

    std::ifstream ifs(inPath, std::ios::binary);
    std::ofstream ofs(outPath, std::ios::binary);
    if (!ifs || !ofs) throw std::runtime_error("File open error");

    std::vector<byte> salt(SALT_LEN), nonce(NONCE_LEN);
    RAND_bytes(salt.data(), SALT_LEN);
    RAND_bytes(nonce.data(), NONCE_LEN);

    std::vector<byte> key;
    deriveKeyFromPassword(password, salt, key);

    ofs.write((char*)MAGIC.data(), MAGIC.size());
    ofs.put(VERSION);
    ofs.write((char*)salt.data(), SALT_LEN);
    ofs.write((char*)nonce.data(), NONCE_LEN);

    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr);
    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, NONCE_LEN, nullptr);
    EVP_EncryptInit_ex(ctx, nullptr, nullptr, key.data(), nonce.data());

    std::vector<byte> in(CHUNK_SIZE), out(CHUNK_SIZE + 16);
    int outlen;

    while (ifs.good()) {
        ifs.read((char*)in.data(), CHUNK_SIZE);
        int read = ifs.gcount();
        if (read <= 0) break;
        EVP_EncryptUpdate(ctx, out.data(), &outlen, in.data(), read);
        ofs.write((char*)out.data(), outlen);
    }

    EVP_EncryptFinal_ex(ctx, out.data(), &outlen);

    std::vector<byte> tag(TAG_LEN);
    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, TAG_LEN, tag.data());
    ofs.write((char*)tag.data(), TAG_LEN);

    EVP_CIPHER_CTX_free(ctx);
    secureClear(key);
}

// ================= DECRYPT =================
void decryptFile(const std::string &inPath,
                 const std::string &outPath,
                 const std::string &password) {

    std::ifstream ifs(inPath, std::ios::binary);
    std::ofstream ofs(outPath, std::ios::binary);
    if (!ifs || !ofs) throw std::runtime_error("File open error");

    ifs.seekg(0, std::ios::end);
    std::streamoff size = ifs.tellg();
    ifs.seekg(0);

    std::array<byte,8> magic;
    ifs.read((char*)magic.data(), magic.size());
    if (magic != MAGIC) throw std::runtime_error("Bad magic");

    ifs.get(); // version

    std::vector<byte> salt(SALT_LEN), nonce(NONCE_LEN), tag(TAG_LEN);
    ifs.read((char*)salt.data(), SALT_LEN);
    ifs.read((char*)nonce.data(), NONCE_LEN);

    ifs.seekg(size - TAG_LEN);
    ifs.read((char*)tag.data(), TAG_LEN);

    std::streamoff cipherStart = MAGIC.size() + 1 + SALT_LEN + NONCE_LEN;
    std::streamoff cipherLen = size - cipherStart - TAG_LEN;
    ifs.seekg(cipherStart);

    std::vector<byte> key;
    deriveKeyFromPassword(password, salt, key);

    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr);
    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, NONCE_LEN, nullptr);
    EVP_DecryptInit_ex(ctx, nullptr, nullptr, key.data(), nonce.data());

    std::vector<byte> in(CHUNK_SIZE), out(CHUNK_SIZE + 16);
    int outlen;

    while (cipherLen > 0) {
        int read = (int)std::min((std::streamoff)CHUNK_SIZE, cipherLen);
        ifs.read((char*)in.data(), read);
        EVP_DecryptUpdate(ctx, out.data(), &outlen, in.data(), read);
        ofs.write((char*)out.data(), outlen);
        cipherLen -= read;
    }

    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, TAG_LEN, tag.data());
    if (EVP_DecryptFinal_ex(ctx, out.data(), &outlen) != 1)
        throw std::runtime_error("Authentication failed");

    EVP_CIPHER_CTX_free(ctx);
    secureClear(key);
}
