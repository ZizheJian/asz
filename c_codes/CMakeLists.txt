cmake_minimum_required(VERSION 3.10)
project(ASTZ_tests)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(BUILD_SHARED_LIBS OFF CACHE BOOL "Build shared libraries" FORCE)

# 优化标志
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Ofast -march=native -mavx2 -mfma -Wno-dangling-else")

add_subdirectory(asz_core)
add_subdirectory(../third_party/csv_tools/c_codes ../build/csv_tools_build)
add_subdirectory(../third_party/zstd ../build/zstd_build)


set(CODE_NAME "" CACHE STRING "which target to build")

if(CODE_NAME STREQUAL "")
    message(FATAL_ERROR "Please provide -DCODE_NAME=<name>")
endif()

set(SRC_FILE "${CODE_NAME}.cpp")

if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${SRC_FILE}")
    message(FATAL_ERROR "Source file ${SRC_FILE} not found")
endif()

add_executable(${CODE_NAME} ${SRC_FILE})
target_link_libraries(${CODE_NAME} PRIVATE libasz libcsv libzstd_static)
install(TARGETS ${CODE_NAME} DESTINATION bin)

if(CODE_NAME STREQUAL "s1_compress")
    add_executable(s1_decompress s1_decompress.cpp)
    target_link_libraries(s1_decompress PRIVATE libasz libcsv libzstd_static)
    install(TARGETS s1_decompress DESTINATION bin)
endif()