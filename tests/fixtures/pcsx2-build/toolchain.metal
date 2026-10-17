// Own compile/link fixture; no GPU execution or original assets.
#include <metal_stdlib>
using namespace metal;

kernel void synthetic_values(device uint* values [[buffer(0)]],
                             uint index [[thread_position_in_grid]]) {
    values[index] = index ^ 0x5a5au;
}
