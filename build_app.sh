#!/bin/bash
set -e

APP_NAME="TranscritorMac"
DISPLAY_NAME="Simple Transcribe"
APP_DIR="${DISPLAY_NAME}.app"
CONTENTS_DIR="${APP_DIR}/Contents"
MACOS_DIR="${CONTENTS_DIR}/MacOS"
RESOURCES_DIR="${CONTENTS_DIR}/Resources"

echo "Limpando build anterior..."
rm -rf "$APP_DIR"
rm -rf "${APP_NAME}.app"

echo "Compilando projeto Swift..."
cd TranscritorMac
swift build -c release
cd ..

echo "Criando estrutura do .app..."
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

echo "Copiando binário executável..."
# O swift build cria o binário na pasta .build/release/
cp TranscritorMac/.build/release/$APP_NAME "$MACOS_DIR/"

echo "Criando Info.plist..."
cat <<EOF > "$CONTENTS_DIR/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleIdentifier</key>
    <string>com.marcosaccioly.transcritormac</string>
    <key>CFBundleName</key>
    <string>Simple Transcribe</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>14.0</string>
</dict>
</plist>
EOF

echo "App empacotado com sucesso em: $APP_DIR"
