#pragma once
#include <cstddef>
#include <cstdint>
#include <vector>

namespace sh3::observer {
enum class RangeDomain { image, aot };
struct RangeOwner { RangeDomain domain{}; std::uint64_t object{}; std::uint32_t part{}; };
struct RangeClaim {
  RangeOwner owner{};
  std::uint64_t address{}, size{}, initialized_size{};
  std::uint32_t protection{};
};
enum class RangeContent { initialized, zero_fill };
struct RangeDependency { std::size_t claim{}; RangeContent content{}; };
struct RangeAtom {
  std::uint64_t address{}, size{};
  std::size_t first_dependency{}, dependency_count{};
  bool conflict{};
};
inline constexpr std::size_t range_claim_capacity = 65536;
inline constexpr std::size_t range_atom_capacity = 3 * range_claim_capacity;
inline constexpr std::size_t range_dependency_capacity = 1048576;
inline constexpr std::uint64_t range_unique_limit = 16ULL * 1024 * 1024 * 1024;
struct RangePlan {
  std::vector<RangeClaim> claims;
  std::vector<RangeAtom> atoms;
  std::vector<RangeDependency> dependencies;
  std::uint64_t declared_bytes{}, reserved_bytes{}, unique_bytes{}, touched_pages{};
  std::uint64_t zero_fill_bytes{}, conflict_bytes{};
  std::size_t empty_claims{};
};
enum class RangePlanFailure { none, invalid, capacity, unavailable };
// Structural coverage only. Completeness and page provenance belong to the caller.
// Input may alias output.claims; failures always clear the entire output.
RangePlanFailure plan_ranges(const std::vector<RangeClaim>&, std::uint64_t page_size,
                             RangePlan&) noexcept;
} // namespace sh3::observer
