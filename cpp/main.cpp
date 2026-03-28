#include <opencv2/opencv.hpp>
#include <iostream>
#include <bitset>
#include <vector>
#include <fstream>

int main() {
    // Step 1: Load the image
    cv::Mat img = cv::imread("../shiva.jpg");
    if (img.empty()) {
        std::cerr << "Error: Could not open image!" << std::endl;
        return -1;
    }

    // Step 2: Convert to grayscale
    cv::Mat gray;
    cv::cvtColor(img, gray, cv::COLOR_BGR2GRAY);

    // Step 3: Save grayscale image (optional)
    cv::imwrite("../gray.jpg", gray);
    std::cout << "Grayscale image saved as gray.jpg" << std::endl;

    // Step 4: Convert the grayscale image to a bit stream
    std::vector<unsigned char> pixels;
    pixels.assign(gray.datastart, gray.dataend);

    std::string bitStream;

    // Convert each pixel to its 8-bit binary representation
    for (unsigned char pixel : pixels) {
        std::bitset<8> bits(pixel);
        bitStream += bits.to_string();
    }

    // Step 5: (Optional) Save the bitstream to a file
    std::ofstream outFile("../bitstream.txt");
    outFile << bitStream;
    outFile.close();

    std::cout << "Bitstream generated successfully!" << std::endl;
    std::cout << "Image size: " << gray.cols << "x" << gray.rows << std::endl;
    std::cout << "Total bits: " << bitStream.size() << std::endl;
    std::cout << "Output saved to bitstream.txt" << std::endl;
    std::cout << "Output saved to bitstream.txt" << std::endl;
    
    return 0;

}
