add_library(libcsv INTERFACE)

# 暴露头文件路径：让链接者（如主程序）能 #include "compressor.h"
target_include_directories(libcsv INTERFACE
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# 可选：安装规则（make install 时，库去 lib/，头文件去 include/）
install(TARGETS libcsv
    DESTINATION lib
)
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR} 
    DESTINATION include 
    FILES_MATCHING PATTERN "*.hpp" PATTERN "*.tpp"
)