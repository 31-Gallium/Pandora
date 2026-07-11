cmake_minimum_required(VERSION 3.20)
project(AudioCaptureService VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Third-party libraries (Header-only)
# include_directories(third_party)

# Source files
set(SOURCES
    src/main.cpp
    src/capture/AudioCapture.cpp
    src/dsp/FFTEngine.cpp
    src/ipc/IPCServer.cpp
)

# Executable
add_executable(${PROJECT_NAME} ${SOURCES})

# Libraries for Windows WASAPI & COM
target_link_libraries(${PROJECT_NAME} PRIVATE
    ole32
    Mmdevapi
)

# Compiler definitions for strict modern C++
if(MSVC)
    target_compile_options(${PROJECT_NAME} PRIVATE /W4 /WX- /permissive-)
    target_compile_definitions(${PROJECT_NAME} PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)
endif()
