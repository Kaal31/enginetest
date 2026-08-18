#include "chained_jmp.hpp"
#include <cassert>
#include <cstdint>

int main() {
    std::uint8_t trampoline[5] = {0xE9, 0, 0, 0, 0};
    const auto original = reinterpret_cast<std::uintptr_t>(trampoline) + 0x1000;
    const auto tramp = reinterpret_cast<std::uintptr_t>(trampoline);

    // Original E9 target is original + 5 + old_rel. Use a small relative
    // displacement and verify the relocated displacement preserves it.
    const std::int32_t old_rel = 0x120;
    *reinterpret_cast<std::int32_t*>(trampoline + 1) = old_rel;

    std::int32_t new_rel = 0;
    assert(enginetest::hook_runtime::relocate_chained_jmp(original, tramp, &new_rel));

    const auto old_target = original + 5 + static_cast<std::intptr_t>(old_rel);
    const auto new_target = tramp + 5 + static_cast<std::intptr_t>(new_rel);
    assert(old_target == new_target);
    return 0;
}
