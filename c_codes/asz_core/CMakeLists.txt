add_library(libasz INTERFACE)

# 设置 C++ 标准（与根项目一致）
set_target_properties(libasz PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED ON
    BUILD_SHARED_LIBS OFF
)

# 暴露头文件路径：让链接者（如主程序）能 #include "compressor.h"
target_include_directories(libasz INTERFACE
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# 可选：安装规则（make install 时，库去 lib/，头文件去 include/）
install(TARGETS libasz
    DESTINATION lib
)
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR} 
    DESTINATION include 
    FILES_MATCHING PATTERN "*.hpp" PATTERN "*.tpp"
)