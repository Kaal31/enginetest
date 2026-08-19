#include "build_fingerprint.hpp"
#include "module_resolver.hpp"
#include "sha256.hpp"

#include <sys/stat.h>

namespace enginetest::runtime {

bool fingerprint_loaded_module(const std::string& module_name,
                               BuildFingerprint* out) {
    if (!out) return false;
    ModuleInfo module;
    if (!find_loaded_module(module_name, &module)) return false;

    out->module_path = module.path;
    out->module_base = module.base;
    out->module_end = module.end;

    struct stat st {};
    if (stat(module.path.c_str(), &st) == 0) {
        out->file_size = static_cast<std::uint64_t>(st.st_size);
    }
    out->sha256 = sha256_file(module.path);
    return !out->sha256.empty();
}

} // namespace enginetest::runtime
