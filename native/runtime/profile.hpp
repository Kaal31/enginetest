#pragma once

#include "build_fingerprint.hpp"
#include <cstdint>
#include <string>
#include <unordered_map>

namespace enginetest::runtime {

// Engine-owned build profile. The common runtime only transports the profile;
// it never invents Steam RVAs or hook targets.
struct Profile {
    std::string engine;
    std::string sha256;
    std::unordered_map<std::string, std::uintptr_t> rvas;
};

class ProfileProvider {
public:
    virtual ~ProfileProvider() = default;
    virtual bool select(const BuildFingerprint& fingerprint, Profile* out) const = 0;
};

} // namespace enginetest::runtime
