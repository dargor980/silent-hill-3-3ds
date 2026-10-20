// Diagnostic-only rejection traces. No new state, ABI or admission decision.
namespace {
void trace_ledger_failure(const char* reason, const ImageSnapshot& state,
                          std::uintptr_t address) noexcept {
  char line[192];
  const int length = std::snprintf(line,sizeof(line),
    "SH3_LEDGER_FAIL reason=%s count=%zu revision=%llu address=%llx\n",
    reason,state.count,static_cast<unsigned long long>(state.revision),
    static_cast<unsigned long long>(address));
  if (length>0 && static_cast<std::size_t>(length)<sizeof(line))
    (void)::write(STDERR_FILENO,line,static_cast<std::size_t>(length));
}
}
ImageLedger::ImageLedger(std::uint64_t initial_revision) noexcept {
  state_.revision = initial_revision;
  failed_ = initial_revision == 0 || initial_revision == std::numeric_limits<std::uint64_t>::max();
  if (failed_) trace_ledger_failure("initial_revision",state_,0);
}
bool ImageLedger::advance() noexcept {
  if (failed_ || state_.revision >= std::numeric_limits<std::uint64_t>::max() - 1) {
    const bool newly_failed = !failed_;
    failed_ = true;
    if (newly_failed) trace_ledger_failure("revision_exhausted",state_,0);
    return false;
  }
  ++state_.revision;
  return true;
}
void ImageLedger::add(std::uintptr_t address) noexcept {
  if (failed_) return;
  if (address == 0 || state_.count == image_capacity) {
    failed_ = true;
    trace_ledger_failure(address==0 ? "null_address" : "capacity",state_,address);
    return;
  }
  for (std::size_t i = 0; i < state_.count; ++i)
    if (state_.addresses[i] == address) {
      failed_ = true;
      trace_ledger_failure("duplicate",state_,address);
      return;
    }
  if (advance()) state_.addresses[state_.count++] = address;
}
void ImageLedger::remove(std::uintptr_t address) noexcept {
  if (failed_) return;
  for (std::size_t i = 0; i < state_.count; ++i) {
    if (state_.addresses[i] == address) {
      if (!advance()) return;
      for (std::size_t j = i + 1; j < state_.count; ++j) state_.addresses[j - 1] = state_.addresses[j];
      state_.addresses[--state_.count] = 0;
      return;
    }
  }
  failed_ = true;
  trace_ledger_failure("unknown_remove",state_,address);
}
