#include "check.hpp"
#include "sh3_observer/admission.hpp"
#include <string>
#include <thread>
using namespace sh3::observer;
constexpr auto mask = (std::uint32_t{1} << admission_condition_count) - 1;
void defaults() {
  const auto r = assess_profile({});
  CHECK(r.violated == 0 && r.unknown == mask);
}
void single() {
  for (std::size_t i = 0; i < admission_condition_count; ++i) {
    AdmissionProfile p; p.fill(AdmissionFact::satisfied);
    const auto bit = std::uint32_t{1} << i;
    p[i] = AdmissionFact::violated;
    auto r = assess_profile(p); CHECK(r.violated == bit && r.unknown == 0);
    p[i] = AdmissionFact::unknown;
    r = assess_profile(p); CHECK(r.unknown == bit && r.violated == 0);
  }
}
void combinations() {
  // Enumerate every violated subset, with all remaining facts unknown.
  for (std::uint32_t bits = 0; bits <= mask; ++bits) {
    AdmissionProfile p{};
    for (std::size_t i = 0; i < p.size(); ++i)
      if (bits & (std::uint32_t{1} << i)) p[i] = AdmissionFact::violated;
    const auto r = assess_profile(p);
    CHECK(r.violated == bits && r.unknown == (mask ^ bits));
  }
}
void invalid() {
  for (unsigned value = 3; value <= 255; ++value) {
    AdmissionProfile p; p.fill(static_cast<AdmissionFact>(value));
    const auto r = assess_profile(p); CHECK(r.unknown == mask && r.violated == 0);
  }
  for (std::size_t i = 0; i < admission_condition_count; ++i)
    CHECK(admission_bit(static_cast<AdmissionCondition>(i)) == (std::uint32_t{1} << i));
  for (unsigned i = admission_condition_count; i <= 255; ++i)
    CHECK(admission_bit(static_cast<AdmissionCondition>(i)) == 0);
}
void independent() {
  AdmissionProfile p; p.fill(AdmissionFact::satisfied);
  auto r = assess_profile(p); CHECK(r.unknown == 0 && r.violated == 0);
  defaults(); p.fill(AdmissionFact::violated);
  r = assess_profile(p); CHECK(r.violated == mask && r.unknown == 0);
  defaults();
}
void concurrent() {
  std::thread a([]{ for (unsigned i=0; i<1000; ++i) defaults(); });
  std::thread b([]{ for (unsigned i=0; i<1000; ++i) independent(); });
  a.join(); b.join();
}
int main(int argc, char** argv) {
  CHECK(argc == 2); const std::string name = argv[1];
  if (name == "defaults") defaults(); else if (name == "single") single();
  else if (name == "combinations") combinations(); else if (name == "invalid") invalid();
  else if (name == "independent") independent(); else if (name == "concurrent") concurrent();
  else CHECK(false);
}
