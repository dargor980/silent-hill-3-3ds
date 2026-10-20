#include "sh3_observer/macos_platform_origin.hpp"
#include <cstdio>

// ABI measurement only: no OS interaction or production-capacity override.
int main() {
  using namespace sh3::observer;
  const auto snapshots = 2 * sizeof(ImageSnapshot);
  const auto indices = sizeof(std::array<std::size_t, image_capacity>);
  std::printf("capacity=%zu snapshot=%zu ledger=%zu mapped_file=%zu image_origin=%zu "
              "platform_provider=%zu strict_sample_arrays=%zu platform_sample_arrays=%zu\n",
              image_capacity, sizeof(ImageSnapshot), sizeof(ImageLedger),
              sizeof(MappedFile), sizeof(ImageOrigin), sizeof(MacOSPlatformOrigins),
              snapshots + indices + sizeof(std::array<MappedFile, image_capacity>),
              snapshots + indices + sizeof(std::array<ImageOrigin, image_capacity>));
}
