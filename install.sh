#!/usr/bin/env bash

set -euo pipefail

PYTHON_VERSION="3.14.7"

# Get project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VENV_DIR="$PROJECT_DIR/.venv"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$BIN_DIR/brender"

echo "================================"
echo " BRender Installer"
echo "================================"
echo
echo "Project: $PROJECT_DIR"
echo


# --------------------------------------------------
# Install uv
# --------------------------------------------------

if command -v uv >/dev/null 2>&1; then
    UV="$(command -v uv)"
else
    echo "[1/5] Installing uv..."

    curl -LsSf https://astral.sh/uv/install.sh | sh

    UV="$HOME/.local/bin/uv"

    if [ ! -x "$UV" ]; then
        echo "ERROR: uv installation failed."
        exit 1
    fi
fi


# --------------------------------------------------
# Install Python
# --------------------------------------------------

echo "[2/5] Installing Python $PYTHON_VERSION..."

"$UV" python install "$PYTHON_VERSION"


# --------------------------------------------------
# Create venv
# --------------------------------------------------

echo "[3/5] Creating virtual environment..."

"$UV" venv \
    --python "$PYTHON_VERSION" \
    "$VENV_DIR"


# --------------------------------------------------
# Install dependencies
# --------------------------------------------------

echo "[4/5] Installing dependencies..."

if [ -f "$PROJECT_DIR/requirements.txt" ]; then

    "$UV" pip install \
        --python "$VENV_DIR/bin/python" \
        -r "$PROJECT_DIR/requirements.txt"

else

    echo "WARNING: requirements.txt not found."

fi


# --------------------------------------------------
# Create brender command
# --------------------------------------------------

echo "[5/5] Creating brender command..."

mkdir -p "$BIN_DIR"

cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash

PROJECT_DIR="$PROJECT_DIR"

exec "\$PROJECT_DIR/.venv/bin/python" \
    "\$PROJECT_DIR/brender.py" \
    "\$@"
EOF

chmod +x "$LAUNCHER"


# --------------------------------------------------
# Add ~/.local/bin to PATH
# --------------------------------------------------

PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'

add_path() {
    FILE="$1"

    if [ -f "$FILE" ]; then
        if ! grep -Fxq "$PATH_LINE" "$FILE"; then
            echo >> "$FILE"
            echo "# Added by BRender installer" >> "$FILE"
            echo "$PATH_LINE" >> "$FILE"
        fi
    fi
}

add_path "$HOME/.bashrc"
add_path "$HOME/.zshrc"


echo
echo "================================"
echo " Installation complete!"
echo "================================"
echo
echo "Run:"
echo
echo "    brender"
echo
echo "If this terminal cannot find it yet,"
echo "restart your shell or run:"
echo
echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
echo