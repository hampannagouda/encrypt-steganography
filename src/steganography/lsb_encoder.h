#ifndef LSB_ENCODER_H
#define LSB_ENCODER_H

#include <string>

void embedDataInImage(const std::string& coverImage,
                      const std::string& dataFile,
                      const std::string& outputImage);

void extractDataFromImage(const std::string& stegoImage,
                          const std::string& outputDataFile);

#endif
