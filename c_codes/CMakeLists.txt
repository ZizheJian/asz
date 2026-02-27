cmake_minimum_required(VERSION 3.10)
project(ASTZ_tests)

# set(CMAKE_CXX_STANDARD 11)
# set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "Build shared libraries" FORCE)

# 优化标志
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Ofast -march=native -fopenmp -mavx2 -mfma -Wno-dangling-else")

add_subdirectory(csv_tools)
add_subdirectory(third_party/zstd)

add_executable(ASTZ_tests main.cpp)
target_link_libraries(ASTZ_tests PRIVATE libcsv libzstd_static)
    
install(TARGETS ASTZ_tests DESTINATION bin)