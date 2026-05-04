@echo off
echo Compiling C++ Encryption CLI...

REM Make sure to run this from the project root directory
g++ -std=c++17 src\encryption\encrypt_cli.cpp src\encryption\aes_gcm_encrypt.cpp -o src\encryption\encrypt_cli.exe -lcrypto

if %errorlevel% neq 0 (
    echo.
    echo Compilation FAILED!
    echo Ensure you have g++ installed and the OpenSSL (-lcrypto) development libraries available.
) else (
    echo.
    echo Compilation SUCCESSFUL!
    echo Executable created at: src\encryption\encrypt_cli.exe
)
pause
