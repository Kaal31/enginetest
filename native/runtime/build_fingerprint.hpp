// Experimental build/profile primitive.
// Kept independent from either Moon or Luma engine ownership.
#pragma once

#include <cstdint>
#include <string>

namespace enginetest::runtime {

struct BuildFingerprint {
    std::string module_path;
    std::uintptr_t module_base = 0;
    std::uintptr_t module_end = 0;
    std::uint64_t file_size = 0;
    std::string sha256;
};

// Collect stable metadata for a loaded ELF module. The implementation does not
// download or choose any hook offsets; engines remain responsible for profiles.
bool fingerprint_loaded_module(const std::string& module_name,
                               BuildFingerprint* out);

} // namespace enginetest::runtime
