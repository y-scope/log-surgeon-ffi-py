cmake_minimum_required(VERSION 3.23)

set(SKBUILD OFF)
set(log_surgeon_ffi_VERSION "0.0.0")
if(DEFINED SKBUILD_PROJECT_NAME)
    set(SKBUILD ON)
    set(log_surgeon_ffi_VERSION "${SKBUILD_PROJECT_VERSION}")
    execute_process(
        COMMAND
            "task" "deps:install-all"
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        COMMAND_ECHO STDOUT
    )
endif()

project(log_surgeon_ffi LANGUAGES CXX VERSION ${log_surgeon_ffi_VERSION})

# C-extension modules will be compiled as shared libraries. To enable dynamic linking, all libraries
# (including the static ones) must be compiled with the position-independent-code option.
set(CMAKE_POSITION_INDEPENDENT_CODE ON CACHE BOOL "Compile libraries using PIC.")

option(BUILD_SHARED_LIBS "Build using shared libraries." OFF)

set(CMAKE_EXPORT_COMPILE_COMMANDS
    ON
    CACHE BOOL
    "Enable/Disable output of compile commands during generation."
    FORCE
)

if(log_surgeon_ffi_IS_TOP_LEVEL)
    # Include dependency settings if the project isn't being included as a subproject.
    # NOTE: We mark the file optional because if the user happens to have the dependencies
    # installed, this file is not necessary.
    include("build/deps/cmake-settings/all.cmake" OPTIONAL)
endif()

find_package(
    Python
    REQUIRED
    COMPONENTS
        Interpreter
        Development.Module
)
message(STATUS "Found Python ${Python_VERSION}.")
python_add_library(log_surgeon_ffi MODULE WITH_SOABI)

find_package(log_surgeon REQUIRED)
message(STATUS "Found log_surgeon ${log_surgeon_VERSION}.")

set(SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")
set(log_surgeon_ffi_SRC_DIR "${SOURCE_DIR}/log_surgeon_ffi")

target_sources(
    log_surgeon_ffi
    PRIVATE
        "${log_surgeon_ffi_SRC_DIR}/api_decoration.hpp"
        "${log_surgeon_ffi_SRC_DIR}/log_surgeon_ffi.cpp"
        "${log_surgeon_ffi_SRC_DIR}/PyExceptionContext.hpp"
        "${log_surgeon_ffi_SRC_DIR}/PyObjectCast.hpp"
        "${log_surgeon_ffi_SRC_DIR}/PyObjectUtils.hpp"
        "${log_surgeon_ffi_SRC_DIR}/PyReaderParser.cpp"
        "${log_surgeon_ffi_SRC_DIR}/PyReaderParser.hpp"
        "${log_surgeon_ffi_SRC_DIR}/utils.cpp"
        "${log_surgeon_ffi_SRC_DIR}/utils.hpp"
)

target_include_directories(
    log_surgeon_ffi
    # PUBLIC
    #     $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>
    #     $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_include_directories(log_surgeon_ffi PRIVATE ${log_surgeon_ffi_SRC_DIR})

target_link_libraries(log_surgeon_ffi PRIVATE log_surgeon::log_surgeon)

target_compile_features(log_surgeon_ffi PRIVATE cxx_std_20)

if(SKBUILD)
    install(TARGETS log_surgeon_ffi LIBRARY DESTINATION ".")

    # Bundle Rust log-mechanic shared library into log_surgeon/ package dir
    set(RUST_LIB_DIR "${CMAKE_SOURCE_DIR}/build/deps/log-mechanic-install")
    if(APPLE)
        set(RUST_LIB_NAME "liblog_mechanic.dylib")
    else()
        set(RUST_LIB_NAME "liblog_mechanic.so")
    endif()
    if(EXISTS "${RUST_LIB_DIR}/${RUST_LIB_NAME}")
        install(FILES "${RUST_LIB_DIR}/${RUST_LIB_NAME}" DESTINATION "log_surgeon")
    else()
        message(WARNING "Rust library not found at ${RUST_LIB_DIR}/${RUST_LIB_NAME}")
    endif()
endif()
