#!/bin/bash
# Build wheels for private dependencies
# This script clones the repos and builds wheels needed for Docker deployment

set -e

echo "Building wheels for tac-aws and twilio-agent-connect..."

# Configuration
TAC_AWS_REPO="https://github.com/twilio-innovation/aws-twilio-agent-connect-python.git"
TAC_AWS_COMMIT="bcf33de54df19a72ea804d7b6682323b14d8b699"

TAC_REPO="https://github.com/twilio-innovation/twilio-agent-connect-python.git"
TAC_COMMIT="ccef428740ae445dd1e25dfa80d1f9c2f82abbf9"

WHEELS_DIR="$(pwd)/wheels"
BUILD_DIR="/tmp/tac-wheels-build"

# Create wheels directory
mkdir -p "$WHEELS_DIR"

# Clean build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo ""
echo "1/4 Cloning tac-aws repository..."
git clone "$TAC_AWS_REPO" "$BUILD_DIR/tac-aws" --quiet
cd "$BUILD_DIR/tac-aws"
git checkout "$TAC_AWS_COMMIT" --quiet

echo "2/4 Building tac-aws wheel..."
python3 -m pip wheel --no-deps . -w "$WHEELS_DIR" --quiet
cd -

echo ""
echo "3/4 Cloning twilio-agent-connect repository..."
git clone "$TAC_REPO" "$BUILD_DIR/tac" --quiet
cd "$BUILD_DIR/tac"
git checkout "$TAC_COMMIT" --quiet

echo "4/4 Building twilio-agent-connect wheel..."
python3 -m pip wheel --no-deps . -w "$WHEELS_DIR" --quiet
cd -

# Clean up
rm -rf "$BUILD_DIR"

echo ""
echo "✓ Wheels built successfully!"
echo ""
ls -lh "$WHEELS_DIR"/*.whl | awk '{print "  " $9, "(" $5 ")"}'
echo ""
echo "You can now build the Docker image with: make docker-build"
