// Experimental EngineTest native runtime.
//
// Adapted from the chained-jump relocation logic in LumaLinux
// (src/lmhook.cpp, GPLv3). This file does not install hooks; it only provides
// the relocation primitive for a trampoline whose original prologue starts
// with x86/x86-64 E9 rel32.
#pragma once

#include <cstdint>

namespace enginetest::hook_runtime {

// Rewrites the rel32 at trampoline+1 so an E9 at the trampoline continues to
// reach the same absolute target it reached from original_function.
//
// Returns false unless trampoline begins with E9. No memory is made writable
// here: callers own the trampoline memory and must perform their own protection
// changes using their chosen hook library.
bool relocate_chained_jmp(std::uintptr_t original_function,
                          std::uintptr_t trampoline,
                          std::int32_t* relocated_rel32);

} // namespace enginetest::hook_runtime
