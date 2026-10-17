#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DEVKITPRO:?Run inside the pinned devkitPro image or provide a verified installation}"
# Preserve a recorded bundle: use a fresh build directory for the next artifact.
if [[ -e build/3ds/debug-bundle.json || -L build/3ds/debug-bundle.json ||
      -e build/3ds/artifact-check.json || -L build/3ds/artifact-check.json ]]; then
  echo "Recorded debug bundle already exists; preserve it and use a clean build directory." >&2
  exit 1
fi
cmake -S . -B build/3ds \
  -DCMAKE_TOOLCHAIN_FILE="$DEVKITPRO/cmake/3DS.cmake" \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF
cmake --build build/3ds --parallel 2
cp tests/fixtures/synthetic/probe.txt build/3ds/probe.txt
python3 -m tools.debug.bundle create --directory build/3ds \
  --build-id "$(cat build/3ds/build-id.txt)"
python3 -m tools.debug.bundle verify --directory build/3ds \
  --build-id "$(cat build/3ds/build-id.txt)"
dkp-pacman -Q > build/3ds/toolchain-packages.txt
sha256sum build/3ds/sh3_diagnostic.3dsx build/3ds/sh3_diagnostic.elf \
  build/3ds/sh3_diagnostic.smdh build/3ds/probe.txt \
  > build/3ds/SHA256SUMS
python3 -m tools.qa.build_artifacts --directory build/3ds \
  --probe tests/fixtures/synthetic/probe.txt --sdk-image toolchains/devkitpro-image.txt --record
