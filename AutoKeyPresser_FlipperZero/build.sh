#!/bin/bash#!/bin/bash

# Build script for Flipper Zero Key Spammer

# Key Spammer Build Script for Flipper Zero

echo "🚀 Building Flipper Zero Key Spammer..."# This script helps you build and deploy the Key Spammer application



# Check if uFBT is installedecho "=== Flipper Zero Key Spammer Build Script ==="

if ! command -v ufbt &> /dev/null; then

    echo "❌ uFBT not found. Please install it first:"# Check if FLIPPER_FW_PATH is set

    echo "   pip3 install --upgrade ufbt"if [ -z "$FLIPPER_FW_PATH" ]; then

    echo "   ufbt update"    echo "Error: Please set FLIPPER_FW_PATH environment variable to your Flipper firmware directory"

    exit 1    echo "Example: export FLIPPER_FW_PATH=/path/to/flipperzero-firmware"

fi    exit 1

fi

# Navigate to source directory

cd src# Check if firmware directory exists

if [ ! -d "$FLIPPER_FW_PATH" ]; then

# Clean previous build    echo "Error: Flipper firmware directory not found: $FLIPPER_FW_PATH"

echo "🧹 Cleaning previous build..."    exit 1

ufbt cleanfi



# Build the application# Copy application to firmware applications_user directory

echo "🔨 Building application..."echo "Copying key_spammer to $FLIPPER_FW_PATH/applications_user/"

ufbtrm -rf "$FLIPPER_FW_PATH/applications_user/key_spammer"

cp -r key_spammer "$FLIPPER_FW_PATH/applications_user/"

if [ $? -eq 0 ]; then

    echo "✅ Build successful!"# Navigate to firmware directory

    echo "📦 Output file: dist/key_spammer.fap"cd "$FLIPPER_FW_PATH"

    echo "🔧 To install: ufbt launch"

else# Build the application

    echo "❌ Build failed!"echo "Building key_spammer application..."

    exit 1./fbt fap_key_spammer

fi
if [ $? -eq 0 ]; then
    echo "=== Build successful! ==="
    echo "FAP file location: build/f7-firmware-D/apps_data/key_spammer/key_spammer.fap"
    echo ""
    echo "To install:"
    echo "1. Copy the .fap file to your Flipper Zero SD card's 'apps' folder"
    echo "2. Or use: ./fbt launch APPSRC=applications_user/key_spammer"
else
    echo "=== Build failed! ==="
    exit 1
fi