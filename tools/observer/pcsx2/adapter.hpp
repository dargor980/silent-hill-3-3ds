#pragma once
#include "sh3_observer/cooperative_gate.hpp"
#include "sh3_observer/capture.hpp"
namespace sh3::observer {
// PINE thread only; queued callback owns its completion and never borrows reply buffers.
Result dispatch(const Request&, CooperativeGate::Work work = {});
}
