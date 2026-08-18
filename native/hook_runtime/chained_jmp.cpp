// Experimental EngineTest native runtime.
// GPLv3-compatible adaptation of the chained-jump arithmetic in LumaLinux
// src/lmhook.cpp. See native/README.md for provenance and scope.
#include "chained_jmp.hpp"

namespace enginetest::hook_runtime {

bool relocate_chained_jmp(std::uintptr_t original_function,
                          std::uintptr_t trampoline,
                          std::int32_t* relocated_rel32) {
    if (!relocated_rel32) return false;
    const auto opcode = *reinterpret_cast<const volatile std::uint8_t*>(trampoline);
    if (opcode != 0xE9) return false;

    const auto old_rel = *reinterpret_cast<const volatile std::int32_t*>(trampoline + 1);
    const auto delta = static_cast<std::intptr_t>(original_function) -
                       static_cast<std::intptr_t>(trampoline);
    *relocated_rel32 = static_cast<std::int32_t>(
        static_cast<std::int64_t>(old_rel) + static_cast<std::int64_t>(delta));
    return true;
}

} // namespace enginetest::hook_runtime
