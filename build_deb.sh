#!/bin/bash
# 构建 voice-typing.deb 安装包
# 用法: ./build_deb.sh
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEBIAN_DIR="$PROJECT_DIR/debian"
BUILD_ROOT="/tmp/voice-typing-deb-build"

cd "$PROJECT_DIR"

# 1. 读取版本号（从 voice_typing/__init__.py）
VERSION=$(python3 -c "from voice_typing import __version__; print(__version__)")
echo "==> 打包版本: $VERSION"

# 2. 更新 control 文件版本号
sed -i "s/^Version: .*/Version: $VERSION/" "$DEBIAN_DIR/DEBIAN/control"

# 3. 清空并重建构建目录
rm -rf "$BUILD_ROOT"
mkdir -p "$BUILD_ROOT"
cp -r "$DEBIAN_DIR"/* "$BUILD_ROOT/"

# 4. 同步最新源码到 debian/usr/share/voice-typing/voice_typing
DEST="$BUILD_ROOT/usr/share/voice-typing/voice_typing"
rm -rf "$DEST"
mkdir -p "$DEST"
rsync -a --exclude='__pycache__' --exclude='*.pyc' "$PROJECT_DIR/voice_typing/" "$DEST/"
echo "==> 源码已同步到 $DEST"

# 5. 同步 main.py
cp "$PROJECT_DIR/main.py" "$BUILD_ROOT/usr/share/voice-typing/main.py"

# 6. 修正权限
find "$BUILD_ROOT" -type d -exec chmod 755 {} +
find "$BUILD_ROOT" -type f -exec chmod 644 {} +
chmod 755 "$BUILD_ROOT/usr/bin/voice-typing"
chmod 755 "$BUILD_ROOT/DEBIAN/postinst"

# 7. 构建 deb 包
OUTPUT_DEB="$PROJECT_DIR/voice-typing_${VERSION}_amd64.deb"
dpkg-deb --build --root-owner-group "$BUILD_ROOT" "$OUTPUT_DEB"

echo ""
echo "==> 构建完成: $OUTPUT_DEB"
echo "==> 安装命令: sudo dpkg -i $OUTPUT_DEB && sudo apt-get install -f"
