#pragma once
// IT02: private-copy instrumentation. No production checks, allocations or IO
// inside measured intervals. Phase totals are inclusive, never additive by default.
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace sh3_it {
using Clock = std::chrono::steady_clock;
inline std::uint64_t ns(Clock::time_point t) noexcept {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(t.time_since_epoch()).count();
}
inline std::uint64_t now() noexcept { return ns(Clock::now()); }
enum Phase : unsigned { prepare, manifest_parse, construct, sample, initial,
  manifest_before, origin_first, origin_second, manifest_after, digest, tail,
  close_work, file_identity, file_read, sha_update, origin_stable, phase_count };
inline constexpr const char* names[] = {"prepare", "manifest_parse", "construct", "sample",
  "initial", "manifest_before", "origin_first", "origin_second", "manifest_after", "digest",
  "tail", "close_work", "file_identity", "file_read", "sha_update", "origin_stable"};
struct Counter {
  std::uint64_t calls{}, complete{}, total{}, minimum{UINT64_MAX}, maximum{}, bytes{}, first{}, last{};
  bool record(std::uint64_t start, std::uint64_t end, bool done, std::uint64_t size) noexcept {
    if (end < start || calls == UINT64_MAX || end-start > UINT64_MAX-total || size > UINT64_MAX-bytes)
      return false;
    const auto elapsed=end-start;
    if (!calls) first=start;
    ++calls; complete+=done; total+=elapsed; bytes+=size; last=end;
    if (elapsed<minimum) minimum=elapsed;
    if (elapsed>maximum) maximum=elapsed;
    return true;
  }
};
struct Event { const char* name{}; unsigned query{}; std::uint64_t at{}, deadline{}; };
struct Data {
  std::array<std::array<Counter,phase_count>,4> counters{};
  std::array<Event,16> events{};
  unsigned query{}, event_count{}, errors{};
  bool fine{}, dumped{};
  std::uint64_t calibration_ns{}, calibration_calls{};
  Data() noexcept {
    const auto* mode=std::getenv("SH3_INVENTORY_TIMING");
    fine=mode && !std::strcmp(mode,"fine");
  }
  void next() noexcept { if(query<3) ++query; else ++errors; }
};
inline thread_local Data data;
class Span {
  Phase phase_; unsigned query_; bool enabled_, stopped_{}, done_{};
  std::uint64_t started_{}, bytes_{};
public:
  explicit Span(Phase phase, bool fine_only=false) noexcept
    : phase_(phase),query_(data.query),enabled_(!fine_only || data.fine) {
    if(enabled_) started_=now();
  }
  Span(const Span&)=delete;
  Span& operator=(const Span&)=delete;
  void done(std::uint64_t bytes=0) noexcept { done_=true;bytes_=bytes; }
  void stop() noexcept {
    if(stopped_ || !enabled_) return;
    const auto ended=now(); stopped_=true;
    if(!data.counters[query_][phase_].record(started_,ended,done_,bytes_)) ++data.errors;
  }
  ~Span() { stop(); }
};
inline void mark(const char* name,unsigned query=0,std::uint64_t deadline=0,std::uint64_t at=0) noexcept {
  if(data.event_count==data.events.size()) { ++data.errors;return; }
  data.events[data.event_count++]={name,query,at?at:now(),deadline};
}
inline volatile std::uint64_t calibration_sink{};
inline void calibrate() noexcept {
  // An isolated accumulator measures two clock reads plus record; not a bound
  // on scheduler interference, branches, TLS, or the whole instrumentation.
  Counter counter;
  const auto start=now();
  for(unsigned i=0;i<10000;++i) { const auto a=now();counter.record(a,now(),true,0); }
  data.calibration_ns=now()-start;data.calibration_calls=counter.calls;
  calibration_sink=counter.total^counter.minimum^counter.maximum^counter.first^counter.last^counter.complete;
}
inline void dump(const char* role) noexcept {
  if(data.dumped) return;
  data.dumped=true;
  for(unsigned q=0;q<4;++q) for(unsigned p=0;p<phase_count;++p) {
    const auto& c=data.counters[q][p];if(!c.calls) continue;
    std::fprintf(stderr,"IT_PHASE role=%s query=%u phase=%s calls=%llu complete=%llu total_ns=%llu min_ns=%llu max_ns=%llu bytes=%llu first_ns=%llu last_ns=%llu\n",
      role,q,names[p],(unsigned long long)c.calls,(unsigned long long)c.complete,
      (unsigned long long)c.total,(unsigned long long)c.minimum,(unsigned long long)c.maximum,
      (unsigned long long)c.bytes,(unsigned long long)c.first,(unsigned long long)c.last);
  }
  for(unsigned i=0;i<data.event_count;++i) { const auto& e=data.events[i];
    std::fprintf(stderr,"IT_EVENT role=%s event=%s query=%u at_ns=%llu deadline_ns=%llu\n",
      role,e.name,e.query,(unsigned long long)e.at,(unsigned long long)e.deadline);
  }
  std::fprintf(stderr,"IT_END role=%s fine=%u errors=%u calibration_calls=%llu calibration_ns=%llu\n",
    role,unsigned(data.fine),data.errors,(unsigned long long)data.calibration_calls,
    (unsigned long long)data.calibration_ns);
  std::fflush(stderr);
}
static_assert(sizeof(Data)<8192);
} // namespace sh3_it
