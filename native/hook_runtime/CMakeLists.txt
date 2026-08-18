cmake_minimum_required(VERSION 3.16)
project(enginetest_hook_runtime LANGUAGES CXX)

add_library(enginetest_hook_runtime STATIC
    chained_jmp.cpp
)

target_include_directories(enginetest_hook_runtime PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_features(enginetest_hook_runtime PUBLIC cxx_std_17)

target_compile_options(enginetest_hook_runtime PRIVATE
    -Wall -Wextra -Wpedantic
)
