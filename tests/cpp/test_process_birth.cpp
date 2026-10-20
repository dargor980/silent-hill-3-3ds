#include "check.hpp"
#include "sh3_observer/process_birth.hpp"
#include <limits>
#include <string>
#include <type_traits>
using namespace sh3::observer;
namespace {
struct Birth final : BirthSource {
  BirthReading value{42, 100, 123456};
  unsigned calls{}, fail_at{}, change_at{};
  BirthReading changed{43, 100, 123456};
  bool read(BirthReading& out) noexcept override {
    ++calls; out = calls == change_at ? changed : value;
    return calls != fail_at;
  }
};
struct Nonce final : NonceSource {
  unsigned calls{};
  bool ok{true};
  ProcessNonce value{{1}};
  bool fill(ProcessNonce& out) noexcept override { ++calls; out = value; return ok; }
};
void rejected(ProcessBirth& identity, Birth& b, Nonce& n, BirthFailure reason) {
  auto result = identity.sample();
  CHECK(result.failure == reason && same_process_key(result.key, {}));
  const auto calls = b.calls, entropy = n.calls;
  b.value = {42,100,123456}; b.change_at = b.fail_at = 0; n.ok = true; n.value = {{1}};
  identity.lose();
  for (unsigned i = 0; i < 3; ++i) {
    result = identity.sample();
    CHECK(result.failure == reason && same_process_key(result.key, {}));
  }
  CHECK(b.calls == calls && n.calls == entropy);
}
void stable() {
  static_assert(!std::is_copy_constructible_v<ProcessBirth> && !std::is_move_constructible_v<ProcessBirth>);
  Birth b; Nonce n; ProcessBirth identity(b,n);
  const auto first = identity.sample();
  CHECK(first.failure == BirthFailure::none && first.key.pid == 42);
  CHECK(first.key.birth_ns == 100123456000ULL && first.key.nonce == n.value);
  n.ok = false; // Revalidation must never regenerate the nonce.
  for (unsigned i = 0; i < 100; ++i) CHECK(same_process_key(first.key,identity.sample().key));
  CHECK(n.calls == 1 && b.calls == 202);
}
void unavailable(bool ready, bool last) {
  Birth b; Nonce n; ProcessBirth identity(b,n);
  if (ready) CHECK(identity.sample().failure == BirthFailure::none);
  b.fail_at = b.calls + (last ? 2 : 1);
  rejected(identity,b,n,BirthFailure::unavailable);
}
void entropy(bool zero) {
  Birth b; Nonce n; ProcessBirth identity(b,n);
  if (zero) n.value = {}; else n.ok = false;
  rejected(identity,b,n,BirthFailure::entropy);
  CHECK(n.calls == 1 && b.calls == 1);
}
void invalid() {
  constexpr auto max = std::numeric_limits<std::uint64_t>::max();
  for (const auto input : {BirthReading{0,100,0}, BirthReading{0x80000000u,100,0},
       BirthReading{42,0,0}, BirthReading{42,100,1000000}, BirthReading{42,max,0},
       BirthReading{42,max/1000000000,999999}}) {
    Birth b; Nonce n; b.value = input; ProcessBirth identity(b,n);
    rejected(identity,b,n,BirthFailure::invalid); CHECK(n.calls == 0);
  }
  Birth b; Nonce n; b.change_at = 2; b.changed = {42,0,0}; ProcessBirth identity(b,n);
  rejected(identity,b,n,BirthFailure::invalid);
}
void upper_bound() {
  constexpr auto max = std::numeric_limits<std::uint64_t>::max();
  Birth b; Nonce n; b.value = {0x7fffffff,max/1000000000,(max%1000000000)/1000};
  n.value = {}; n.value.back() = 1; ProcessBirth identity(b,n);
  const auto value = identity.sample();
  CHECK(value.failure == BirthFailure::none && value.key.birth_ns == max-max%1000);
}
void changed(bool ready, bool last, bool pid) {
  Birth b; Nonce n; ProcessBirth identity(b,n);
  if (ready) CHECK(identity.sample().failure == BirthFailure::none);
  b.changed = pid ? BirthReading{43,100,123456} : BirthReading{42,100,123457};
  if (ready && !last) b.value = b.changed; // Persistent replacement, not just an unstable read.
  else b.change_at = b.calls + (last ? 2 : 1);
  rejected(identity,b,n,BirthFailure::changed);
}
void lose(bool ready) {
  Birth b; Nonce n; ProcessBirth identity(b,n);
  if (ready) CHECK(identity.sample().failure == BirthFailure::none);
  identity.lose(); rejected(identity,b,n,BirthFailure::lost);
}
void equality() {
  const ProcessKey a{42,1000,{{1}}};
  CHECK(same_process_key(a,a));
  CHECK(!same_process_key(a,{43,1000,{{1}}}));
  CHECK(!same_process_key(a,{42,2000,{{1}}}));
  CHECK(!same_process_key(a,{42,1000,{{2}}}));
}
}
int main(int argc, char** argv) {
  CHECK(argc == 2); const std::string name = argv[1];
  if (name == "stable") stable();
  else if (name == "unavailable_first") unavailable(false,false);
  else if (name == "unavailable_last") unavailable(false,true);
  else if (name == "lost_read_first") unavailable(true,false);
  else if (name == "lost_read_last") unavailable(true,true);
  else if (name == "entropy_error") entropy(false);
  else if (name == "entropy_zero") entropy(true);
  else if (name == "invalid") invalid();
  else if (name == "upper_bound") upper_bound();
  else if (name == "unstable_pid") changed(false,true,true);
  else if (name == "unstable_birth") changed(false,true,false);
  else if (name == "pid_change") changed(true,false,true);
  else if (name == "pid_reuse") changed(true,false,false);
  else if (name == "pid_change_late") changed(true,true,true);
  else if (name == "pid_reuse_late") changed(true,true,false);
  else if (name == "lose_empty") lose(false);
  else if (name == "lose_ready") lose(true);
  else if (name == "equality") equality();
  else CHECK(false);
}
