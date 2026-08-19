cmake_minimum_required(VERSION 3.16)
project(enginetest_runtime LANGUAGES CXX)

add_library(enginetest_runtime STATIC
    module_resolver.cpp
    build_fingerprint.cpp
)

target_include_directories(enginetest_runtime PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_features(enginetest_runtime PUBLIC cxx_std_17)

target_compile_options(enginetest_runtime PRIVATE
    -Wall -Wextra -Wpedantic
)
