#include "module_resolver.hpp"

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <thread>

namespace enginetest::runtime {

static bool parse_maps_line(const char* line, ModuleInfo* out, const std::string& wanted) {
    if (!line || !out) return false;
    unsigned long long start = 0, end = 0;
    char perms[5] = {};
    unsigned long long offset = 0;
    unsigned int dev_major = 0, dev_minor = 0;
    unsigned long inode = 0;
    char path[4096] = {};

    const int n = std::sscanf(line, "%llx-%llx %4s %llx %x:%x %lu %4095[^
]",
                              &start, &end, perms, &offset,
                              &dev_major, &dev_minor, &inode, path);
    if (n < 7) return false;

    std::string mapped = (n == 8) ? path : std::string();
    const auto first = mapped.find_first_not_of(' ');
    if (first != std::string::npos) mapped.erase(0, first);
    if (mapped.find(wanted) == std::string::npos) return false;

    out->path = mapped;
    out->base = static_cast<std::uintptr_t>(start);
    out->end = static_cast<std::uintptr_t>(end);
    return true;
}

bool find_loaded_module(const std::string& module_name, ModuleInfo* out) {
    if (!out || module_name.empty()) return false;
    std::ifstream maps("/proc/self/maps");
    if (!maps) return false;

    std::string line;
    while (std::getline(maps, line)) {
        ModuleInfo candidate;
        if (parse_maps_line(line.c_str(), &candidate, module_name)) {
            *out = std::move(candidate);
            return true;
        }
    }
    return false;
}

bool wait_for_module(const std::string& module_name,
                     ModuleInfo* out,
                     int timeout_ms,
                     int poll_ms) {
    if (poll_ms <= 0) poll_ms = 50;
    const auto started = std::chrono::steady_clock::now();

    for (;;) {
        if (find_loaded_module(module_name, out)) return true;
        if (timeout_ms >= 0) {
            const auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::steady_clock::now() - started).count();
            if (elapsed >= timeout_ms) return false;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(poll_ms));
    }
}

} // namespace enginetest::runtime
