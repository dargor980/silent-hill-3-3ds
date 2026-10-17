#!/usr/bin/env bash
# Build the pinned SDK example twice without modifying SDK sources.
set -euo pipefail
repo_root=$(cd "$(dirname "$0")/.." && pwd)
if (( $# > 1 )); then
  echo "Usage: bash scripts/check_3ds_toolchain.sh [new-output-directory]" >&2
  exit 2
fi
output=${1:-"$repo_root/build/toolchain-check"}
if [[ -e "$output" || -L "$output" ]]; then
  echo "Output already exists; choose a new directory: $output" >&2
  exit 2
fi
: "${DEVKITPRO:?Run inside the pinned devkitPro image; DEVKITPRO is required}"
: "${DEVKITARM:?Run inside the pinned devkitPro image; DEVKITARM is required}"
example="$DEVKITPRO/examples/3ds/graphics/gpu/simple_tri"
for input in "$DEVKITARM/3ds_rules" "$DEVKITARM/base_rules" "$DEVKITARM/base_tools" \
  "$DEVKITARM/bin/arm-none-eabi-g++" "$example/Makefile" \
  "$example/source/main.c" "$example/source/vshader.v.pica" \
  "$DEVKITPRO/examples/3ds/README.md" "$DEVKITPRO/libctru/default_icon.png"; do
  if [[ ! -f "$input" ]]; then
    echo "Incomplete SDK; missing required file: $input" >&2
    exit 2
  fi
done
export PATH="$DEVKITARM/bin:$DEVKITPRO/tools/bin:$PATH"
for tool in make dkp-pacman arm-none-eabi-g++ arm-none-eabi-readelf \
  picasso bin2s smdhtool 3dsxtool sha256sum cmp; do
  command -v "$tool" >/dev/null || { echo "Missing build tool: $tool" >&2; exit 2; }
done
# Prevent inherited make settings from turning the check into a dry run.
unset MAKEFLAGS MFLAGS MAKEOVERRIDES
mkdir -p -- "$(dirname "$output")"
mkdir -- "$output"
output=$(cd "$output" && pwd)
cp -- "$repo_root/toolchains/devkitpro-image.txt" "$output/expected-sdk-image.txt"
dkp-pacman -Q > "$output/toolchain-packages.txt"
{
  uname -m
  arm-none-eabi-g++ --version
  make --version
} > "$output/versions.txt"
cp -- "$DEVKITPRO/examples/3ds/README.md" "$output/examples-README.md"
sha256sum "$DEVKITPRO/examples/3ds/README.md" "$DEVKITPRO/libctru/default_icon.png" \
  "$DEVKITARM/3ds_rules" "$DEVKITARM/base_rules" "$DEVKITARM/base_tools" \
  > "$output/sdk-inputs.sha256"

for run in run-1 run-2; do
  # Copy the inspected inputs, never any prebuilt objects from the SDK tree.
  mkdir -p -- "$output/$run/simple_tri/source"
  cp -- "$example/Makefile" "$output/$run/simple_tri/Makefile"
  cp -- "$example/source/main.c" "$example/source/vshader.v.pica" \
    "$output/$run/simple_tri/source/"
  (
    cd "$output/$run/simple_tri"
    sha256sum Makefile source/main.c source/vshader.v.pica
  ) > "$output/$run-sources.sha256"
  if ! make -C "$output/$run/simple_tri" -j2 > "$output/$run.log" 2>&1; then
    cat "$output/$run.log" >&2
    exit 1
  fi
  for extension in 3dsx elf smdh; do
    test -s "$output/$run/simple_tri/simple_tri.$extension"
  done
  arm-none-eabi-readelf -h "$output/$run/simple_tri/simple_tri.elf" \
    > "$output/$run-elf-header.txt"
done
cmp "$output/run-1-sources.sha256" "$output/run-2-sources.sha256"
# ELF debug paths differ between directories; compare deployable outputs.
for extension in 3dsx smdh; do
  cmp "$output/run-1/simple_tri/simple_tri.$extension" \
    "$output/run-2/simple_tri/simple_tri.$extension"
done

if ! arm-none-eabi-g++ -std=c++17 -Wall -Wextra -Werror \
  -march=armv6k -mtune=mpcore -mfloat-abi=hard -mtp=soft \
  -D__3DS__ -I"$DEVKITPRO/libctru/include" \
  -c "$repo_root/tests/fixtures/synthetic/toolchain/cxx17.cpp" \
  -o "$output/cxx17.o" > "$output/cxx17.log" 2>&1; then
  cat "$output/cxx17.log" >&2
  exit 1
fi
arm-none-eabi-readelf -h "$output/cxx17.o" > "$output/cxx17-elf-header.txt"
(
  cd "$output"
  sha256sum run-{1,2}/simple_tri/simple_tri.{3dsx,elf,smdh} cxx17.o
) > "$output/SHA256SUMS"
printf '%s\n' 'PASS: official simple_tri built twice; 3DSX/SMDH identical; C++17 ARM compiled.' \
  > "$output/result.txt"
cat "$output/result.txt"
