// Own integration for the fixed private PCSX2 source copy; not linked into the port.
#ifndef SH3_ENABLE_OBSERVER
#error Observer adapter requires explicit opt-in
#endif
#include "Common.h"
#include "Host.h"
#include "MemoryTypes.h"
#include "R5900.h"
#include "VMManager.h"
#include "vtlb.h"
#include "adapter.hpp"
#include "sh3_observer/completion.hpp"
#include <cstring>
#include <memory>
#include <unistd.h>

namespace sh3::observer {
static_assert(sizeof(uptr) == 8);
static_assert(sizeof(vtlb_private::VTLBVirtual) == 8);
static_assert(vtlb_private::VTLB_PAGE_SIZE == page_size);
static_assert(vtlb_private::VTLB_VMAP_ITEMS == (1U << 20));
static_assert(Ps2MemSize::MainRam == ram_size);
static_assert(offsetof(EEVM_MemoryAllocMess, Main) == 0);
static_assert(sizeof(cpuRegs.pc) == 4 && sizeof(cpuRegs.cycle) == 8);
namespace {
class EmulatorReader final : public Reader {
  static bool anchors() noexcept {
    const auto base = reinterpret_cast<std::uintptr_t>(eeMem);
    const auto table = reinterpret_cast<std::uintptr_t>(vtlb_private::vtlbdata.vmap);
    return base >= page_size && base <= sign_bit - ram_size && base % page_size == 0 &&
      table >= 8 && table <= sign_bit - (std::uint64_t{1} << 23) && table % 8 == 0 &&
      Ps2MemSize::ExposedRam == ram_size;
  }
public:
  Snapshot snapshot(const Request& r) noexcept override {
    Snapshot s{};
    s.pid = static_cast<std::uint64_t>(getpid());
    if (VMManager::GetState() != VMState::Paused) return s;
    s.flags = 1;
    if (VMManager::HasPendingSaveStateWrites()) {s.flags |= 2; return s;}
    if (!anchors()) return s;
    s.pc = cpuRegs.pc; s.cycle = cpuRegs.cycle;
    s.game_crc = VMManager::GetDiscCRC();
    s.ee_main = reinterpret_cast<std::uintptr_t>(eeMem->Main);
    s.vmap = reinterpret_cast<std::uintptr_t>(vtlb_private::vtlbdata.vmap);
    s.exposed_ram = Ps2MemSize::ExposedRam;
    const auto end = std::uint64_t{r.virtual_start} + r.size;
    s.page_count = static_cast<std::uint32_t>((end - 1) / page_size - r.virtual_start / page_size + 1);
    for (unsigned i = 0; i < s.page_count; ++i) {
      const auto page = r.virtual_start / page_size + i;
      s.pages[i] = {page, vtlb_private::vtlbdata.vmap[page].raw()};
    }
    return s;
  }
  bool read_ram(std::uint32_t offset, std::uint32_t size, std::uint8_t* output) noexcept override {
    if (VMManager::GetState() != VMState::Paused || !anchors() ||
        size == 0 || size > page_size || offset > ram_size - size) return false;
    std::memcpy(output, eeMem->Main + offset, size);
    return true;
  }
};
} // namespace
Result dispatch(const Request& request, CooperativeGate::Work work) {
  if (!valid_request(request)) return failure(request, Status::request);
  const auto completion = std::make_shared<Completion>(request);
  Host::RunOnCPUThread([completion, work = std::move(work)] {
    (void)work; // Retain the PINE reservation through timeout and callback disposal.
    EmulatorReader reader;
    completion->run(reader);
  }, false);
  return completion->wait(std::chrono::milliseconds(2000));
}
} // namespace sh3::observer
