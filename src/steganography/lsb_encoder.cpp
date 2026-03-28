#include "lsb_encoder.h"

#include <fstream>
#include <vector>
#include <stdexcept>
#include <cstdint>
#include <iostream>

using byte = unsigned char;

/* ===================== Utility ===================== */

static std::vector<byte> readBinaryFile(const std::string& path) {
    std::ifstream ifs(path, std::ios::binary);
    if (!ifs) throw std::runtime_error("Cannot open file: " + path);
    return std::vector<byte>((std::istreambuf_iterator<char>(ifs)),
                              std::istreambuf_iterator<char>());
}

static void writeBinaryFile(const std::string& path, const std::vector<byte>& data) {
    std::ofstream ofs(path, std::ios::binary);
    if (!ofs) throw std::runtime_error("Cannot write file: " + path);
    ofs.write(reinterpret_cast<const char*>(data.data()), data.size());
}

/* ===================== EMBED ===================== */

void embedDataInImage(const std::string& coverImage,
                      const std::string& dataFile,
                      const std::string& outputImage) {

    std::vector<byte> image = readBinaryFile(coverImage);
    std::vector<byte> data  = readBinaryFile(dataFile);

    uint32_t dataSize = static_cast<uint32_t>(data.size());

    // total bits needed = size(32 bits) + data bits
    size_t requiredBits = 32 + (data.size() * 8);
    if (requiredBits > image.size()) {
        throw std::runtime_error("Cover image is too small to hold encrypted data");
    }

    size_t imgIndex = 0;

    // ---- Embed data size (32 bits) ----
    for (int i = 31; i >= 0; --i) {
        image[imgIndex] &= 0xFE;
        image[imgIndex] |= (dataSize >> i) & 1;
        imgIndex++;
    }

    // ---- Embed actual data ----
    for (byte b : data) {
        for (int i = 7; i >= 0; --i) {
            image[imgIndex] &= 0xFE;
            image[imgIndex] |= (b >> i) & 1;
            imgIndex++;
        }
    }

    writeBinaryFile(outputImage, image);
}

/* ===================== EXTRACT ===================== */

void extractDataFromImage(const std::string& stegoImage,
                          const std::string& outputDataFile) {

    std::vector<byte> image = readBinaryFile(stegoImage);

    size_t imgIndex = 0;
    uint32_t dataSize = 0;

    // ---- Extract data size (32 bits) ----
    for (int i = 0; i < 32; ++i) {
        dataSize = (dataSize << 1) | (image[imgIndex] & 1);
        imgIndex++;
    }

    std::vector<byte> extracted(dataSize);

    // ---- Extract data ----
    for (uint32_t i = 0; i < dataSize; ++i) {
        byte b = 0;
        for (int j = 0; j < 8; ++j) {
            b = (b << 1) | (image[imgIndex] & 1);
            imgIndex++;
        }
        extracted[i] = b;
    }

    writeBinaryFile(outputDataFile, extracted);
}
