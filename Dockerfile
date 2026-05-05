FROM python:3.10-slim

WORKDIR /app

# Install build tools and OpenSSL for C++ compilation
RUN apt-get update && apt-get install -y \
    g++ \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Compile C++ encryption tool
RUN g++ -std=c++17 src/encryption/encrypt_cli.cpp src/encryption/aes_gcm_encrypt.cpp -o src/encryption/encrypt_cli -lcrypto

# Default command to run the interactive pipeline
CMD ["python", "pipeline.py"]