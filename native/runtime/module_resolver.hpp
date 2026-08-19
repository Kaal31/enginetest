// Experimental EngineTest runtime primitives inspired by LumaLinux.
// No Steam hooks are installed by this component.
#pragma once

#include <cstdint>
#include <string>

namespace enginetest::runtime {

struct ModuleInfo {
    std::string path;
    std::uintptr_t base = 0;
    std::uintptr_t end = 0;
};

// Resolve the first loaded module whose mapped path contains module_name.
// Returns false when the module is not currently mapped.
bool find_loaded_module(const std::string& module_name, ModuleInfo* out);

// Wait for a module to become mapped. timeout_ms == 0 performs one immediate
// lookup; a negative timeout waits indefinitely.
bool wait_for_module(const std::string& module_name,
                     ModuleInfo* out,
                     int timeout_ms,
                     int poll_ms = 50);

} // namespace enginetest::runtime
