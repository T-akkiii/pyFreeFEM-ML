#!/bin/bash
# FreeFEM mmap-semaphore プラグインインストールスクリプト

# 必要なコマンドが存在するか確認
command -v make >/dev/null 2>&1 || { echo "Error: make command not found"; exit 1; }
command -v g++ >/dev/null 2>&1 || { echo "Error: g++ compiler not found"; exit 1; }
command -v FreeFem++ >/dev/null 2>&1 || { echo "Error: FreeFem++ not found"; exit 1; }

echo "===== FreeFEM mmap-semaphore プラグインインストーラー ====="

# 現在のディレクトリをスクリプトのディレクトリに変更
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# FreeFEMのインクルードディレクトリを探す
FREEFEM_INCLUDE=""
POSSIBLE_INCLUDE_DIRS=(
  "/usr/local/include/freefem"
  "/usr/include/freefem"
  "/usr/local/include/freefem++"
  "/usr/include/freefem++"
)

for dir in "${POSSIBLE_INCLUDE_DIRS[@]}"; do
  if [ -d "$dir" ]; then
    FREEFEM_INCLUDE="$dir"
    break
  fi
done

if [ -z "$FREEFEM_INCLUDE" ]; then
  echo "Error: FreeFEM include directory not found"
  exit 1
fi

echo "FreeFEM include directory: $FREEFEM_INCLUDE"

# FreeFEMのライブラリディレクトリを探す
FREEFEM_LIB=""
POSSIBLE_LIB_DIRS=(
  "/usr/local/lib/ff++"
  "/usr/lib/ff++"
  "/usr/local/lib/freefem++"
  "/usr/lib/freefem++"
)

for dir in "${POSSIBLE_LIB_DIRS[@]}"; do
  if [ -d "$dir" ]; then
    FREEFEM_LIB="$dir"
    break
  fi
done

if [ -z "$FREEFEM_LIB" ]; then
  echo "Error: FreeFEM library directory not found"
  exit 1
fi

# FreeFEMのバージョンを取得
FREEFEM_VERSION=$(FreeFem++ -v | grep -oE '[0-9]+\.[0-9]+' | head -1)
if [ -z "$FREEFEM_VERSION" ]; then
  FREEFEM_VERSION="4.10" # デフォルトバージョン
  echo "Warning: Could not determine FreeFEM version, using default: $FREEFEM_VERSION"
else
  echo "Detected FreeFEM version: $FREEFEM_VERSION"
fi

# プラグインのインストール先ディレクトリを設定
PLUGIN_INSTALL_DIR="$FREEFEM_LIB/$FREEFEM_VERSION"
if [ ! -d "$PLUGIN_INSTALL_DIR" ]; then
  echo "Creating plugin directory: $PLUGIN_INSTALL_DIR"
  mkdir -p "$PLUGIN_INSTALL_DIR"
fi

echo "Plugin will be installed to: $PLUGIN_INSTALL_DIR"

# ソースディレクトリに移動
cd src

# プラグインのコンパイル
echo "Compiling mmap-semaphore plugin..."
g++ -std=c++11 -fPIC -shared -o mmap-semaphore.so mmap-semaphore.cpp -I"$FREEFEM_INCLUDE" -lrt

if [ $? -ne 0 ]; then
  echo "Error: Failed to compile the plugin"
  exit 1
fi

echo "Plugin compiled successfully"

# プラグインのインストール
echo "Installing plugin to $PLUGIN_INSTALL_DIR..."
cp mmap-semaphore.so "$PLUGIN_INSTALL_DIR/" || { echo "Error: Failed to copy plugin"; exit 1; }

echo "Creating lib directory if it doesn't exist..."
mkdir -p "$PLUGIN_INSTALL_DIR/lib"
echo "Copying plugin to lib directory..."
cp mmap-semaphore.so "$PLUGIN_INSTALL_DIR/lib/" || { echo "Warning: Failed to copy plugin to lib directory"; }

# 実行権限を設定
chmod +x "$PLUGIN_INSTALL_DIR/mmap-semaphore.so" || { echo "Warning: Failed to set execute permission"; }
chmod +x "$PLUGIN_INSTALL_DIR/lib/mmap-semaphore.so" 2>/dev/null || true

echo "===== プラグインのインストールが完了しました ====="
echo "FreeFEMスクリプトからプラグインを使用するには、以下のコマンドを実行してください:"
echo "load \"mmap-semaphore\""
echo ""
echo "環境変数の設定（Pythonスクリプトから利用する場合）:"
echo "export FF_LOADPATH=$PLUGIN_INSTALL_DIR"
echo "export FF_INCLUDEPATH=$PLUGIN_INSTALL_DIR/idp"
echo ""
echo "これらの環境変数を ~/.bashrc に追加することをお勧めします。" 