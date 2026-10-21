#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DEVKITPRO:?Run inside the pinned devkitPro image}"
output="${1:-build/animation-probe}"
if [[ -e "$output" || -L "$output" ]]; then
  echo "Material probe output already exists; select a fresh directory." >&2
  exit 1
fi
cmake -S . -B "$output" \
  -DCMAKE_TOOLCHAIN_FILE="$DEVKITPRO/cmake/3DS.cmake" \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF
cmake --build "$output" --target sh3_animation_probe_3dsx --parallel 2
dkp-pacman -Q > "$output/toolchain-packages.txt"
cp toolchains/devkitpro-image.txt "$output/sdk-image.txt"
cd "$output"
for artifact in sh3_animation_probe.elf sh3_animation_probe.3dsx sh3_animation_probe.smdh \
    build-id.txt toolchain-packages.txt sdk-image.txt; do
  test -s "$artifact"
done
sha256sum sh3_animation_probe.elf sh3_animation_probe.3dsx sh3_animation_probe.smdh \
  build-id.txt toolchain-packages.txt sdk-image.txt > SHA256SUMS
sha256sum --check SHA256SUMS
