#pragma once

#include <array>
#include <cstdint>
#include <string>

namespace enginetest::runtime {

// Small self-contained SHA-256 implementation used only for build
// fingerprinting. No network/profile selection is performed here.
std::string sha256_file(const std::string& path);

} // namespace enginetest::runtime
