CMAKE_MINIMUM_REQUIRED(VERSION 3.12)
PROJECT(Couchstore)

set(CMAKE_POSITION_INDEPENDENT_CODE ON)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if (WIN32)
    message(FATAL_ERROR "No Windows")
endif ()

INCLUDE(CheckFunctionExists)
INCLUDE(CheckIncludeFile)
INCLUDE(CheckIncludeFiles)
INCLUDE(CheckLibraryExists)
INCLUDE(CheckSymbolExists)
INCLUDE(CheckTypeSize)
INCLUDE(CTest)
INCLUDE(GenerateExportHeader)
INCLUDE(FetchContent)
INCLUDE(CMakePushCheckState)
INCLUDE(ExternalProject)
INCLUDE(ProcessorCount)

ProcessorCount(COUCHSTORE_BUILD_JOBS)
if (COUCHSTORE_BUILD_JOBS EQUAL 0)
    set(COUCHSTORE_BUILD_JOBS 1)
endif ()
message(STATUS "Using ${COUCHSTORE_BUILD_JOBS} parallel jobs for third-party builds")

set(FETCHCONTENT_UPDATES_DISCONNECTED ON CACHE BOOL "Disconnect FetchContent updates")

cmake_policy(SET CMP0052 OLD)
cmake_policy(SET CMP0079 NEW)

macro(cb_enable_unity_build target)
endmacro()

macro(cb_add_test_executable name)
    add_executable(${name} ${ARGN})
endmacro()

macro(ENABLE_CODE_COVERAGE_REPORT)
endmacro()

INCLUDE_DIRECTORIES(BEFORE ${CMAKE_INSTALL_PREFIX}/include
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CMAKE_CURRENT_SOURCE_DIR}/src
        ${CMAKE_CURRENT_BINARY_DIR}
        ${CMAKE_CURRENT_SOURCE_DIR})

if (LUA_FOUND)
    include_directories(AFTER SYSTEM {LUA_INCLUDE_DIR})
endif (LUA_FOUND)

CHECK_INCLUDE_FILES("netinet/in.h" HAVE_NETINET_IN_H)
CHECK_INCLUDE_FILES("inttypes.h" HAVE_INTTYPES_H)
CHECK_INCLUDE_FILES("unistd.h" HAVE_UNISTD_H)
CHECK_SYMBOL_EXISTS(fdatasync "unistd.h" HAVE_FDATASYNC)
CHECK_SYMBOL_EXISTS(qsort_r "stdlib.h" HAVE_QSORT_R)

SET(COUCHSTORE_FILE_OPS "src/os.cc")

# Disabling Undefined sanitize checks for the file mapreduce.cc since v8::Platform was wrapped in unique_ptr
# and UBSan was unable to lookup symbols for it, thus leading to undefined-behaviour errors
IF (DEFINED UNDEFINED_SANITIZER_FLAG_DISABLE)
    SEPARATE_ARGUMENTS(ubsan_disable_list UNIX_COMMAND ${UNDEFINED_SANITIZER_FLAG_DISABLE})
    SET_PROPERTY(SOURCE src/views/mapreduce/mapreduce.cc
            APPEND
            PROPERTY COMPILE_OPTIONS ${ubsan_disable_list})
ENDIF ()

FetchContent_Declare(
        boost
        GIT_REPOSITORY https://github.com/couchbasedeps/boost.git
        GIT_TAG v1.82.0
)
FetchContent_GetProperties(boost)
if (NOT boost_POPULATED)
    FetchContent_Populate(boost)
endif ()

if (NOT EXISTS "${boost_BINARY_DIR}/include/boost/version.hpp")
    set(boost_DIST_DIR ${boost_SOURCE_DIR}/boost-dist)

    execute_process(
            COMMAND ${boost_DIST_DIR}/bootstrap.sh
            --prefix=${boost_BINARY_DIR}
            --with-libraries=container,context,chrono,date_time,filesystem,program_options,regex,system,thread
            WORKING_DIRECTORY ${boost_DIST_DIR}
            RESULT_VARIABLE boost_bootstrap_result
    )
    if (NOT boost_bootstrap_result EQUAL 0)
        message(FATAL_ERROR "Boost bootstrap failed")
    endif ()

    execute_process(
            COMMAND ${boost_DIST_DIR}/b2
            -j ${COUCHSTORE_BUILD_JOBS}
            --prefix=${boost_BINARY_DIR}
            address-model=64
            link=static
            runtime-link=shared
            threading=multi
            variant=release
            cxxflags=-std=c++17
            cxxflags=-fPIC
            install
            WORKING_DIRECTORY ${boost_DIST_DIR}
            RESULT_VARIABLE boost_build_result
    )
    if (NOT boost_build_result EQUAL 0)
        message(FATAL_ERROR "Boost build failed")
    endif ()
endif ()

set(BOOST_ROOT ${boost_BINARY_DIR} CACHE PATH "Boost root" FORCE)
set(BOOST_NO_SYSTEM_PATHS ON CACHE BOOL "No system Boost" FORCE)
set(BOOST_USE_STATIC_LIBS ON CACHE BOOL "Use static Boost libs" FORCE)
set(BOOST_LINK_STATIC ON CACHE STRING "Link Boost statically" FORCE)

set(BOOST_INCLUDE_DIR ${boost_BINARY_DIR}/include CACHE PATH "Boost include dir" FORCE)
set(BOOST_LIBRARY_DIR ${boost_BINARY_DIR}/lib CACHE PATH "Boost library dir" FORCE)

include_directories(BEFORE ${boost_BINARY_DIR}/include)

add_compile_definitions(BOOST_STACKTRACE_GNU_SOURCE_NOT_REQUIRED)

FetchContent_Declare(
        double-conversion
        GIT_REPOSITORY https://github.com/couchbasedeps/double-conversion.git
        GIT_TAG v3.3.0
)
FetchContent_MakeAvailable(double-conversion)
set(DOUBLE_CONVERSION_INCLUDE_DIR
        "${double-conversion_SOURCE_DIR}" CACHE PATH "double-conversion include dir" FORCE)
set(DOUBLE_CONVERSION_LIBRARY
        double-conversion CACHE STRING "double-conversion library target" FORCE)

FetchContent_Declare(
        GoogleTest
        GIT_REPOSITORY https://github.com/couchbasedeps/googletest.git
        GIT_TAG v1.17.0
)
FetchContent_MakeAvailable(GoogleTest)

set(GFLAGS_BUILD_STATIC_LIBS ON CACHE BOOL "" FORCE)
set(GFLAGS_BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(GFLAGS_BUILD_GFLAGS_LIB ON CACHE BOOL "" FORCE)
set(GFLAGS_BUILD_GFLAGS_NOSTATIC_LIBS OFF CACHE BOOL "" FORCE)
set(GFLAGS_BUILD_GFLAGS_NOTHREADS_LIB ON CACHE BOOL "" FORCE)

FetchContent_Declare(
        gflags
        GIT_REPOSITORY https://github.com/couchbasedeps/gflags.git
        GIT_TAG v2.2.2
)

FetchContent_MakeAvailable(gflags)
if (TARGET gflags AND NOT TARGET gflags::gflags)
    add_library(gflags::gflags ALIAS gflags)
endif ()

set(LIBGFLAGS_LIBRARY gflags CACHE INTERNAL "" FORCE)
set(LIBGFLAGS_LIBRARY_RELEASE gflags CACHE INTERNAL "" FORCE)
set(LIBGFLAGS_LIBRARY_DEBUG gflags CACHE INTERNAL "" FORCE)
set(LIBGFLAGS_INCLUDE_DIR "${gflags_SOURCE_DIR}/include" CACHE INTERNAL "" FORCE)
set(LIBGFLAGS_FOUND TRUE CACHE INTERNAL "" FORCE)

if (TARGET gflags_nothreads_static AND NOT TARGET gflags::gflags_nothreads_static)
    add_library(gflags::gflags_nothreads_static ALIAS gflags_nothreads_static)
endif ()

FetchContent_Declare(
        fast_float
        GIT_REPOSITORY https://github.com/couchbasedeps/fast_float.git
        GIT_TAG v7.0.0
)
FetchContent_MakeAvailable(fast_float)
set(FASTFLOAT_INCLUDE_DIR
        "${fast_float_SOURCE_DIR}/include" CACHE PATH "fast_float include dir" FORCE)

FetchContent_Declare(
        openssl
        GIT_REPOSITORY https://github.com/couchbasedeps/openssl.git
        GIT_TAG openssl-3.6.1
)
FetchContent_GetProperties(openssl)
if (NOT openssl_POPULATED)
    FetchContent_Populate(openssl)
endif ()

if (NOT EXISTS "${openssl_BINARY_DIR}/include/openssl/configuration.h")
    execute_process(
            COMMAND perl ${openssl_SOURCE_DIR}/Configure
            --prefix=${openssl_BINARY_DIR}
            --openssldir=${openssl_BINARY_DIR}/ssl
            --libdir=lib
            no-shared
            no-tests
            WORKING_DIRECTORY ${openssl_SOURCE_DIR}
            RESULT_VARIABLE openssl_configure_result
            OUTPUT_VARIABLE openssl_configure_stdout
            ERROR_VARIABLE openssl_configure_stderr
    )
    message(STATUS "OpenSSL Configure stdout:\n${openssl_configure_stdout}")
    message(STATUS "OpenSSL Configure stderr:\n${openssl_configure_stderr}")
    if (NOT openssl_configure_result EQUAL 0)
        message(FATAL_ERROR
                "OpenSSL Configure failed (exit code: ${openssl_configure_result})\n"
                "Source dir: ${openssl_SOURCE_DIR}\n"
                "Binary dir: ${openssl_BINARY_DIR}\n"
                "stdout:\n${openssl_configure_stdout}\n"
                "stderr:\n${openssl_configure_stderr}")
    endif ()

    execute_process(
            COMMAND make -j ${COUCHSTORE_BUILD_JOBS}
            WORKING_DIRECTORY ${openssl_SOURCE_DIR}
            RESULT_VARIABLE openssl_build_result
            OUTPUT_VARIABLE openssl_build_stdout
            ERROR_VARIABLE openssl_build_stderr
    )
    if (NOT openssl_build_result EQUAL 0)
        message(FATAL_ERROR
                "OpenSSL build failed (exit code: ${openssl_build_result})\n"
                "stdout:\n${openssl_build_stdout}\n"
                "stderr:\n${openssl_build_stderr}")
    endif ()

    execute_process(
            COMMAND make install_sw
            WORKING_DIRECTORY ${openssl_SOURCE_DIR}
            RESULT_VARIABLE openssl_install_result
            OUTPUT_VARIABLE openssl_install_stdout
            ERROR_VARIABLE openssl_install_stderr
    )
    if (NOT openssl_install_result EQUAL 0)
        message(FATAL_ERROR
                "OpenSSL install failed (exit code: ${openssl_install_result})\n"
                "stdout:\n${openssl_install_stdout}\n"
                "stderr:\n${openssl_install_stderr}")
    endif ()
endif ()
set(OPENSSL_ROOT_DIR ${openssl_BINARY_DIR} CACHE PATH "OpenSSL root dir" FORCE)
set(OPENSSL_INCLUDE_DIR ${openssl_BINARY_DIR}/include CACHE PATH "OpenSSL include dir" FORCE)
set(OPENSSL_CRYPTO_LIBRARY ${openssl_BINARY_DIR}/lib/libcrypto.a CACHE FILEPATH "OpenSSL crypto lib" FORCE)
set(OPENSSL_SSL_LIBRARY ${openssl_BINARY_DIR}/lib/libssl.a CACHE FILEPATH "OpenSSL ssl lib" FORCE)
if (NOT TARGET OpenSSL::Crypto)
    add_library(OpenSSL::Crypto STATIC IMPORTED GLOBAL)
    set_target_properties(OpenSSL::Crypto PROPERTIES
            IMPORTED_LOCATION "${OPENSSL_CRYPTO_LIBRARY}"
            INTERFACE_INCLUDE_DIRECTORIES "${OPENSSL_INCLUDE_DIR}")
endif ()
if (NOT TARGET OpenSSL::SSL)
    add_library(OpenSSL::SSL STATIC IMPORTED GLOBAL)
    set_target_properties(OpenSSL::SSL PROPERTIES
            IMPORTED_LOCATION "${OPENSSL_SSL_LIBRARY}"
            INTERFACE_INCLUDE_DIRECTORIES "${OPENSSL_INCLUDE_DIR}"
            INTERFACE_LINK_LIBRARIES OpenSSL::Crypto)
endif ()

FetchContent_Declare(
        libevent
        GIT_REPOSITORY https://github.com/couchbasedeps/libevent.git
        GIT_TAG release-2.1.12-stable
)
set(EVENT__DISABLE_OPENSSL ON CACHE BOOL "" FORCE)
set(EVENT__DISABLE_REGRESS ON CACHE BOOL "" FORCE)
set(EVENT__DISABLE_TESTS ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(libevent)
if (NOT TARGET libevent::core)
    add_library(libevent::core ALIAS event_core)
endif ()
# Force the variable to a known target if you must use a variable
set(LIBEVENT_LIB libevent::core CACHE INTERNAL "" FORCE)
set(LIBEVENT_LIB_RELEASE libevent::core CACHE INTERNAL "" FORCE)
set(LIBEVENT_LIB_DEBUG libevent::core CACHE INTERNAL "" FORCE)
set(LIBEVENT_LIBRARIES ${LIBEVENT_LIB} CACHE INTERNAL "")
set(LIBEVENT_FOUND TRUE CACHE INTERNAL "" FORCE)
set(LibEvent_FOUND TRUE CACHE INTERNAL "" FORCE)

set(LIBEVENT_INCLUDE_DIR
        "${libevent_SOURCE_DIR}/include" CACHE PATH "libevent include dir" FORCE)

FetchContent_Declare(
        simdutf
        GIT_REPOSITORY https://github.com/couchbasedeps/simdutf.git
        GIT_TAG v7.0.0
)

FetchContent_MakeAvailable(simdutf)
set_target_properties(simdutf PROPERTIES POSITION_INDEPENDENT_CODE ON)

FetchContent_Declare(
        zlib
        GIT_REPOSITORY https://github.com/couchbasedeps/zlib.git
        GIT_TAG v1.3.1
)
FetchContent_MakeAvailable(zlib)
set_target_properties(zlib PROPERTIES POSITION_INDEPENDENT_CODE ON)

set(ZLIB_INCLUDE_DIR "${zlib_SOURCE_DIR}" CACHE PATH "" FORCE)
set(ZLIB_INCLUDE_DIRS "${zlib_SOURCE_DIR};${zlib_BINARY_DIR}" CACHE STRING "" FORCE)
set(ZLIB_LIBRARY zlib CACHE STRING "" FORCE)
set(ZLIB_LIBRARIES zlib CACHE STRING "" FORCE)
set(ZLIB_FOUND TRUE CACHE BOOL "" FORCE)

if (NOT TARGET ZLIB::ZLIB)
    add_library(ZLIB::ZLIB ALIAS zlib)
endif ()

FetchContent_Declare(
        spdlog
        GIT_REPOSITORY https://github.com/couchbasedeps/spdlog.git
        GIT_TAG v1.16.0
)
FetchContent_MakeAvailable(spdlog)
if (NOT TARGET spdlog::spdlog)
    add_library(spdlog::spdlog INTERFACE IMPORTED GLOBAL)
endif ()

set(BENCHMARK_USE_BUNDLED_GTEST OFF CACHE BOOL "Use bundled gtest" FORCE)

FetchContent_Declare(
        benchmark
        GIT_REPOSITORY https://github.com/couchbasedeps/benchmark.git
        GIT_TAG v1.9.4
)
FetchContent_MakeAvailable(benchmark)

set(SNAPPY_BUILD_TESTS OFF CACHE BOOL "Snappy build tests" FORCE)
set(SNAPPY_BUILD_BENCHMARKS OFF CACHE BOOL "Snappy build benchmarks" FORCE)

FetchContent_Declare(
        snappy
        GIT_REPOSITORY https://github.com/couchbasedeps/snappy.git
        GIT_TAG 1.2.2
)
set(SNAPPY_INCLUDE_DIR "${snappy_SOURCE_DIR}" CACHE PATH "snappy include dir" FORCE)
set(SNAPPY_LIBRARY snappy CACHE STRING "snappy library target" FORCE)
set(SNAPPY_LIBRARIES snappy CACHE STRING "snappy libraries target" FORCE)
FetchContent_MakeAvailable(snappy)
set_target_properties(snappy PROPERTIES POSITION_INDEPENDENT_CODE ON)

set(WITH_GFLAGS OFF CACHE BOOL "" FORCE)
set(GLOG_USE_GFLAGS OFF CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(GLOG_BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(GLOG_BUILD_STATIC_LIBS ON CACHE BOOL "" FORCE)

FetchContent_Declare(
        glog
        GIT_REPOSITORY https://github.com/couchbasedeps/glog.git
        GIT_TAG v0.7.1
)

set(_saved ${BUILD_SHARED_LIBS})
set(BUILD_SHARED_LIBS OFF)
FetchContent_MakeAvailable(glog)
if (NOT TARGET glog::glog)
    add_library(glog::glog ALIAS glog)
endif ()
set(GLOG_FOUND TRUE CACHE BOOL "" FORCE)
set(GLOG_LIBRARY glog CACHE INTERNAL "" FORCE)
set(GLOG_LIBRARIES glog CACHE INTERNAL "" FORCE)
set(GLOG_LIBRARY_RELEASE glog CACHE INTERNAL "" FORCE)
set(GLOG_LIBRARY_DEBUG glog CACHE INTERNAL "" FORCE)
set(BUILD_SHARED_LIBS ${_saved})

set(_glog_public_include ${glog_BINARY_DIR}/public-include)
if (NOT EXISTS ${_glog_public_include}/glog/logging.h)
    file(COPY ${glog_SOURCE_DIR}/src/glog DESTINATION ${_glog_public_include})
endif ()

set(GLOG_INCLUDE_DIR "${_glog_public_include}" CACHE STRING "glog include dir" FORCE)
set_target_properties(glog PROPERTIES
        INTERFACE_INCLUDE_DIRECTORIES "$<BUILD_INTERFACE:${_glog_public_include}>;$<BUILD_INTERFACE:${glog_BINARY_DIR}>")
target_compile_definitions(glog PUBLIC
        GOOGLE_GLOG_DLL_DECL=
        GLOG_NO_ABBREVIATED_SEVERITIES
)
add_compile_definitions(GLOG_USE_GLOG_EXPORT)
set_target_properties(glog PROPERTIES POSITION_INDEPENDENT_CODE ON)
set_target_properties(glog PROPERTIES CXX_STANDARD 14)

set(GLOG_INCLUDE_DIR "${_glog_public_include};${glog_BINARY_DIR}" CACHE STRING "glog include dir" FORCE)
set(GLOG_FOUND TRUE CACHE BOOL "" FORCE)
set(GLOG_LIBRARIES glog CACHE STRING "" FORCE)

include_directories(BEFORE ${_glog_public_include} ${glog_BINARY_DIR})

FetchContent_Declare(
        folly
        GIT_REPOSITORY https://github.com/couchbasedeps/folly.git
        GIT_TAG v2025.01.20.00
        PATCH_COMMAND patch -N folly/lang/Align.h < "${CMAKE_CURRENT_LIST_DIR}/patches/folly_align_interference.patch" || true
)

FetchContent_GetProperties(folly)
if (NOT folly_POPULATED)
    FetchContent_Populate(folly)

    file(WRITE ${folly_SOURCE_DIR}/CMake/FindLibEvent.cmake "set(LibEvent_FOUND TRUE)\nset(LIBEVENT_LIB libevent::core)\nset(LIBEVENT_INCLUDE_DIR \"${libevent_SOURCE_DIR}/include\")\n")
    file(WRITE ${folly_SOURCE_DIR}/CMake/FindGlog.cmake "set(GLOG_FOUND TRUE)\nset(GLOG_LIBRARY glog)\nset(GLOG_INCLUDE_DIR \"${_glog_public_include}\")\n")
    file(WRITE ${folly_SOURCE_DIR}/build/fbcode_builder/CMake/FindLibEvent.cmake "set(LibEvent_FOUND TRUE)\nset(LIBEVENT_LIB libevent::core)\nset(LIBEVENT_INCLUDE_DIR \"${libevent_SOURCE_DIR}/include\")\n")
    file(WRITE ${folly_SOURCE_DIR}/build/fbcode_builder/CMake/FindGlog.cmake "set(GLOG_FOUND TRUE)\nset(GLOG_LIBRARY glog)\nset(GLOG_INCLUDE_DIR \"${_glog_public_include}\")\n")
endif()

set(_old_build_shared_libs ${BUILD_SHARED_LIBS})
set(_old_skip_install ${CMAKE_SKIP_INSTALL_RULES})
set(BUILD_SHARED_LIBS OFF)
set(CMAKE_SKIP_INSTALL_RULES TRUE)
set(LIBEVENT_LIB libevent::core)
set(GLOG_LIBRARY glog)
add_subdirectory(${folly_SOURCE_DIR} ${folly_BINARY_DIR} EXCLUDE_FROM_ALL)
set(CMAKE_SKIP_INSTALL_RULES ${_old_skip_install})
set(BUILD_SHARED_LIBS ${_old_build_shared_libs})

if (TARGET folly AND NOT TARGET Folly::folly)
    add_library(Folly::folly ALIAS folly)
endif ()

if (TARGET folly AND NOT TARGET Folly::headers)
    add_library(folly_headers_internal INTERFACE)

    target_link_libraries(folly_headers_internal INTERFACE folly glog)
    set_target_properties(folly_headers_internal PROPERTIES
            INTERFACE_INCLUDE_DIRECTORIES "${folly_SOURCE_DIR}"
            INTERFACE_COMPILE_DEFINITIONS "FOLLY_NO_CONFIG=1;FOLLY_HAVE_CLOCK_GETTIME=1"
            INTERFACE_LINK_LIBRARIES "glog")

    add_library(Folly::headers ALIAS folly_headers_internal)
endif ()

FetchContent_Declare(
        json
        GIT_REPOSITORY https://github.com/couchbasedeps/json.git
        GIT_TAG v3.12.0
)
FetchContent_MakeAvailable(json)
if (NOT TARGET nlohmann_json::nlohmann_json)
    add_library(nlohmann_json::nlohmann_json ALIAS nlohmann_json)
endif ()

FetchContent_Declare(
        gsl
        GIT_REPOSITORY https://github.com/couchbasedeps/gsl-lite.git
        GIT_TAG v0.42.0
)
FetchContent_MakeAvailable(gsl)
if (NOT TARGET gsl::gsl-lite)
    add_library(gsl::gsl-lite ALIAS gsl-lite)
endif ()

FetchContent_Declare(
        fmt
        GIT_REPOSITORY https://github.com/couchbasedeps/fmt.git
        GIT_TAG 12.1.0
)
FetchContent_MakeAvailable(fmt)
set_target_properties(fmt PROPERTIES POSITION_INDEPENDENT_CODE ON)

FetchContent_Declare(
        libsodium
        GIT_REPOSITORY https://github.com/couchbasedeps/libsodium.git
        GIT_TAG 1.0.21-RELEASE
)
FetchContent_GetProperties(libsodium)
if (NOT libsodium_POPULATED)
    FetchContent_Populate(libsodium)
endif ()

if (NOT EXISTS "${libsodium_BINARY_DIR}/include/sodium.h")
    execute_process(
            COMMAND ./configure --prefix=${libsodium_BINARY_DIR}
            WORKING_DIRECTORY ${libsodium_SOURCE_DIR}
    )

    execute_process(
            COMMAND make -j ${COUCHSTORE_BUILD_JOBS}
            WORKING_DIRECTORY ${libsodium_SOURCE_DIR}
    )

    execute_process(
            COMMAND make install
            WORKING_DIRECTORY ${libsodium_SOURCE_DIR}
    )
endif ()

if (NOT TARGET libsodium::libsodium)
    add_library(libsodium::libsodium STATIC IMPORTED GLOBAL)

    set_target_properties(libsodium::libsodium PROPERTIES
            IMPORTED_LOCATION ${libsodium_BINARY_DIR}/lib/libsodium.a
            INTERFACE_INCLUDE_DIRECTORIES ${libsodium_BINARY_DIR}/include
    )
endif ()

FetchContent_Declare(
        platform
        GIT_REPOSITORY https://github.com/couchbase/platform.git
        GIT_TAG master
        PATCH_COMMAND patch -N include/cbcrypto/file_reader.h < "${CMAKE_CURRENT_LIST_DIR}/patches/cbcrypto_optional.patch" || true
)
FetchContent_MakeAvailable(platform)
target_include_directories(platform PUBLIC ${fmt_SOURCE_DIR}/include ${zlib_SOURCE_DIR} ${platform_SOURCE_DIR}/cbcrypto)
target_link_libraries(platform PUBLIC fmt::fmt zlib libsodium::libsodium)

FetchContent_Declare(
        phosphor
        GIT_REPOSITORY https://github.com/couchbase/phosphor.git
        GIT_TAG master
)
FetchContent_MakeAvailable(phosphor)

# Create two object libraries, one for the core couchstore code
ADD_LIBRARY(couchstore_objs OBJECT
        src/arena.cc
        src/bitfield.cc
        src/btree_modify.cc
        src/btree_read.cc
        src/couch_cxx_util.cc
        src/couch_db.cc
        src/couch_file_read.cc
        src/couch_file_write.cc
        src/couch_latency.cc
        src/couch_save.cc
        src/crc32.cc
        src/db_compact.cc
        src/file_merger.cc
        src/file_sorter.cc
        src/iobuffer.cc
        src/node_types.cc
        src/quicksort.c
        src/reduces.cc
        src/stream.cc
        src/strerror.cc
        src/tree_writer.cc
        src/util.cc
        ${COUCHSTORE_FILE_OPS})
TARGET_COMPILE_DEFINITIONS(couchstore_objs PUBLIC -Dcouchstore_EXPORTS)
TARGET_LINK_LIBRARIES(couchstore_objs PUBLIC Folly::headers nlohmann_json::nlohmann_json gsl::gsl-lite fmt::fmt platform)
SET_PROPERTY(TARGET couchstore_objs PROPERTY POSITION_INDEPENDENT_CODE 1)
cb_enable_unity_build(couchstore_objs)

# second object library is for the view specific code
ADD_LIBRARY(couchstore_view_objs OBJECT
        src/views/bitmap.cc
        src/views/collate_json.cc
        src/views/encoding.cc
        src/views/file_merger.cc
        src/views/file_sorter.cc
        src/views/index_header.cc
        src/views/keys.cc
        src/views/mapreduce/mapreduce.cc
        src/views/mapreduce/mapreduce_c.cc
        src/views/reducers.cc
        src/views/reductions.cc
        src/views/sorted_list.cc
        src/views/spatial.cc
        src/views/spatial_modify.cc
        src/views/util.cc
        src/views/values.cc
        src/views/view_group.cc
        src/views/purgers.cc
        src/views/compaction.cc
        $<TARGET_OBJECTS:couchstore_objs>)
TARGET_COMPILE_DEFINITIONS(couchstore_view_objs PUBLIC -Dcouchstore_EXPORTS)
TARGET_LINK_LIBRARIES(couchstore_view_objs PUBLIC Folly::headers cbcrypto)
SET_PROPERTY(TARGET couchstore_view_objs PROPERTY POSITION_INDEPENDENT_CODE 1)
cb_enable_unity_build(couchstore_view_objs)

# libcouchstore, core couchstore library
ADD_LIBRARY(couchstore SHARED $<TARGET_OBJECTS:couchstore_objs>)
SET(COUCHSTORE_LIBS cbcompress
        cbcrypto
        platform
        phosphor
        fmt::fmt
        glog::glog)
TARGET_LINK_LIBRARIES(couchstore ${COUCHSTORE_LIBS})

GENERATE_EXPORT_HEADER(couchstore
        EXPORT_MACRO_NAME LIBCOUCHSTORE_API
        EXPORT_FILE_NAME ${CMAKE_CURRENT_BINARY_DIR}/include/libcouchstore/visibility.h
        NO_EXPORT_MACRO_NAME STATIC
        STATIC_DEFINE LIBCOUCHSTORE_NO_VISIBILITY)

ADD_LIBRARY(couchstore_static STATIC $<TARGET_OBJECTS:couchstore_objs>)
TARGET_LINK_LIBRARIES(couchstore_static ${COUCHSTORE_LIBS})
target_compile_definitions(couchstore_static PUBLIC LIBCOUCHSTORE_NO_VISIBILITY)
if (CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    target_compile_options(couchstore_objs PRIVATE
            -Werror=shorten-64-to-32
            -Werror=implicit-int-conversion)
endif ()

TARGET_INCLUDE_DIRECTORIES(couchstore_objs PUBLIC ${CMAKE_CURRENT_BINARY_DIR}/include ${phosphor_SOURCE_DIR}/include)
TARGET_INCLUDE_DIRECTORIES(couchstore_view_objs PUBLIC ${CMAKE_CURRENT_BINARY_DIR}/include)
TARGET_INCLUDE_DIRECTORIES(couchstore PUBLIC ${CMAKE_CURRENT_BINARY_DIR}/include ${phosphor_SOURCE_DIR}/include)
TARGET_INCLUDE_DIRECTORIES(couchstore_static PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${CMAKE_CURRENT_BINARY_DIR}/include)

# libcouchstore_views - core couchstore library + view code and is dependent on
# v8 and icu libraries
ADD_LIBRARY(couchstore_views SHARED
        $<TARGET_OBJECTS:couchstore_objs>
        $<TARGET_OBJECTS:couchstore_view_objs>)
SET(COUCHSTORE_VIEW_LIBS ${COUCHSTORE_LIBS} ${V8_LIBRARIES} ${ICU_LIBRARIES})
SET(COUCHSTORE_VIEW_LIBS_WITHOUT_GLOBAL_NEW_REPLACEMENT ${V8_LIBRARIES} ${ICU_LIBRARIES}
        cbcompress cbcrypto platform phosphor)
TARGET_LINK_LIBRARIES(couchstore_views ${COUCHSTORE_VIEW_LIBS_WITHOUT_GLOBAL_NEW_REPLACEMENT})
TARGET_INCLUDE_DIRECTORIES(couchstore_views PUBLIC ${CMAKE_CURRENT_BINARY_DIR}/include)

add_library(couchstore_program_utilities OBJECT
        src/program_getopt.cc
        src/program_getopt.h)
target_link_libraries(couchstore_program_utilities PUBLIC platform cbcrypto)
target_compile_definitions(couchstore_program_utilities
        PRIVATE DESTINATION_ROOT="${CMAKE_INSTALL_PREFIX}"
        PRODUCT_VERSION="${PRODUCT_VERSION}")

ADD_EXECUTABLE(couch_dbdump
        src/dbdump.cc
        src/tracking_file_ops.cc
        $<TARGET_OBJECTS:couchstore_objs>
        $<TARGET_OBJECTS:couchstore_view_objs>)
target_compile_definitions(couch_dbdump
        PRIVATE DESTINATION_ROOT="${CMAKE_INSTALL_PREFIX}"
        PRODUCT_VERSION="${PRODUCT_VERSION}")
SET_TARGET_PROPERTIES(couch_dbdump PROPERTIES COMPILE_FLAGS "-DLIBCOUCHSTORE_NO_VISIBILITY=1")
TARGET_INCLUDE_DIRECTORIES(couch_dbdump
        PRIVATE
        ${CMAKE_CURRENT_BINARY_DIR}/include
        ${FLATBUFFERS_INCLUDE_DIR})

TARGET_LINK_LIBRARIES(couch_dbdump
        mcbp
        xattr
        ep-engine_collections
        ep-engine_storage_common
        ${COUCHSTORE_VIEW_LIBS} gsl::gsl-lite)

ADD_EXECUTABLE(couch_check
        src/check.cc)

TARGET_LINK_LIBRARIES(couch_check couchstore platform)

ADD_EXECUTABLE(couch_dbck src/dbck.cc)
TARGET_LINK_LIBRARIES(couch_dbck couchstore platform couchstore_program_utilities)

ADD_EXECUTABLE(couch_dbinfo src/dbinfo.cc)
TARGET_COMPILE_DEFINITIONS(couch_dbinfo
        PRIVATE DESTINATION_ROOT="${CMAKE_INSTALL_PREFIX}")
TARGET_LINK_LIBRARIES(couch_dbinfo PRIVATE couchstore platform couchstore_program_utilities)

ADD_EXECUTABLE(couch_compact src/compactor.cc)
TARGET_LINK_LIBRARIES(couch_compact couchstore platform couchstore_program_utilities)

ADD_EXECUTABLE(couch_view_file_merger src/views/bin/couch_view_file_merger.cc src/views/bin/util.cc)
TARGET_LINK_LIBRARIES(couch_view_file_merger couchstore_views)

ADD_EXECUTABLE(couch_view_index_builder src/views/bin/couch_view_index_builder.cc src/views/bin/util.cc)
TARGET_LINK_LIBRARIES(couch_view_index_builder couchstore_views)
TARGET_INCLUDE_DIRECTORIES(couch_view_index_builder PUBLIC ${CMAKE_CURRENT_BINARY_DIR}/include)

ADD_EXECUTABLE(couch_view_group_cleanup src/views/bin/couch_view_group_cleanup.cc src/views/bin/util.cc)
TARGET_LINK_LIBRARIES(couch_view_group_cleanup couchstore_views)
TARGET_INCLUDE_DIRECTORIES(couch_view_group_cleanup PUBLIC ${CMAKE_CURRENT_BINARY_DIR}/include)

ADD_EXECUTABLE(couch_view_index_updater src/views/bin/couch_view_index_updater.cc src/views/bin/util.cc)
TARGET_LINK_LIBRARIES(couch_view_index_updater couchstore_views)
TARGET_INCLUDE_DIRECTORIES(couch_view_index_updater PUBLIC ${CMAKE_CURRENT_BINARY_DIR}/include)

ADD_EXECUTABLE(couch_view_group_compactor src/views/bin/couch_view_group_compactor.cc src/views/bin/util.cc)
TARGET_LINK_LIBRARIES(couch_view_group_compactor couchstore_views)
TARGET_INCLUDE_DIRECTORIES(couch_view_group_compactor PUBLIC ${CMAKE_CURRENT_BINARY_DIR}/include)

cb_add_test_executable(couch_create src/couch_create.cc src/crc32.cc)
TARGET_LINK_LIBRARIES(couch_create couchstore platform gsl::gsl-lite)
TARGET_INCLUDE_DIRECTORIES(couch_create PUBLIC ${CMAKE_CURRENT_BINARY_DIR}/include)

IF (APPLE)
    SET_TARGET_PROPERTIES(couchstore
            PROPERTIES
            INSTALL_RPATH "@loader_path")
ENDIF (APPLE)

INSTALL(TARGETS
        couchstore
        couchstore_views
        couch_dbdump
        couch_dbinfo
        couch_dbck
        couch_compact
        couch_check
        couch_view_file_merger
        couch_view_index_builder
        couch_view_group_cleanup
        couch_view_index_updater
        couch_view_group_compactor
        RUNTIME DESTINATION bin
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib)

CONFIGURE_FILE(${CMAKE_CURRENT_SOURCE_DIR}/config.cmake.h.in
        ${CMAKE_CURRENT_BINARY_DIR}/couchstore_config.h)

# Tests:
IF (LUA_FOUND)
    cb_add_test_executable(couchscript src/couchscript.cc)
    SET_TARGET_PROPERTIES(couchscript PROPERTIES COMPILE_FLAGS
            -I${LUA_INCLUDE_DIR})
    TARGET_LINK_LIBRARIES(couchscript couchstore ${LUA_LIBRARIES})

    ADD_TEST(couchstore-localdoc
            couchscript ${CMAKE_CURRENT_SOURCE_DIR}/tests/localdoc.lua)
    ADD_TEST(couchstore-corrupt
            couchscript ${CMAKE_CURRENT_SOURCE_DIR}/tests/corrupt.lua)
    ADD_TEST(couchstore-bulk
            couchscript ${CMAKE_CURRENT_SOURCE_DIR}/tests/bulk.lua)
    ADD_TEST(couchstore-changes-since-filter
            couchscript ${CMAKE_CURRENT_SOURCE_DIR}/tests/changessincefilter.lua)
    ADD_TEST(couchstore-compact
            couchscript ${CMAKE_CURRENT_SOURCE_DIR}/tests/compact.lua)
    ADD_TEST(couchstore-dropdel
            couchscript ${CMAKE_CURRENT_SOURCE_DIR}/tests/dropdel.lua)
    ADD_TEST(couchstore-largefile
            couchscript ${CMAKE_CURRENT_SOURCE_DIR}/tests/largefile.lua)
    ADD_TEST(couchstore-large
            couchscript ${CMAKE_CURRENT_SOURCE_DIR}/tests/large.lua)
ENDIF (LUA_FOUND)

FUNCTION(M_ADD_PYTHON_TEST name pyfile)
    # Python tests don't work under UBSan - it reports missing symbols when
    # loading libcouchstore.so and it's dependancies:
    #     OSError: libphosphor.so: undefined symbol: __ubsan_vptr_type_cache
    IF (CB_UNDEFINEDSANITIZER)
        RETURN()
    ENDIF ()

    ADD_TEST(${name} ${PYTHON_EXE} ${pyfile})
    SET_PROPERTY(TEST ${name} PROPERTY ENVIRONMENT
            "PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR}/python"
            "LD_LIBRARY_PATH=${CMAKE_CURRENT_BINARY_DIR}:${CMAKE_INSTALL_PREFIX}/lib")

    # If building with TSan, we need to explicitly load the TSan
    # runtime library via LD_PRELOAD, as while libcouchstore.so does
    # link to it, the tsan runtime lib needs to be loaded at process
    # startup - it's too late if we wait until libcouchstore.co is
    # dlopen()'d.
    IF (CB_THREADSANITIZER)
        LIST(APPEND ld_preload libtsan.so.2)
    ENDIF ()
    IF (ld_preload AND UNIX AND NOT APPLE)
        string(REPLACE ";" " " ld_preload_str "${ld_preload}")
        SET_PROPERTY(TEST ${name} APPEND PROPERTY ENVIRONMENT
                "LD_PRELOAD=${ld_preload_str}")
    ENDIF ()
ENDFUNCTION()

M_ADD_PYTHON_TEST(couchstore-purge ${CMAKE_CURRENT_SOURCE_DIR}/tests/purge.py)
M_ADD_PYTHON_TEST(couchstore-rewind ${CMAKE_CURRENT_SOURCE_DIR}/tests/rewind.py)
M_ADD_PYTHON_TEST(couchstore-changecount ${CMAKE_CURRENT_SOURCE_DIR}/tests/changecount.py)
M_ADD_PYTHON_TEST(couchstore-new_delete_replacement
        ${CMAKE_CURRENT_SOURCE_DIR}/tests/new_delete_replacement.py)

MACRO(M_MAKE_LEGACY_TEST name)
    cb_add_test_executable(${name} ${ARGN})
    SET_TARGET_PROPERTIES(${name} PROPERTIES
            COMPILE_FLAGS "-DLIBCOUCHSTORE_NO_VISIBILITY=1")
    TARGET_LINK_LIBRARIES(${name} couchstore_views)
    TARGET_INCLUDE_DIRECTORIES(${name} PUBLIC ${CMAKE_CURRENT_BINARY_DIR}/include)
ENDMACRO()

M_MAKE_LEGACY_TEST(couchstore_file-deduper-test
        src/file_merger.cc
        tests/file_deduper_tests.cc)

M_MAKE_LEGACY_TEST(couchstore_file-merger-test
        src/file_merger.cc
        tests/file_merger_tests.cc)

M_MAKE_LEGACY_TEST(couchstore_file-sorter-test
        src/file_merger.cc
        src/file_sorter.cc
        src/quicksort.c
        tests/file_sorter_tests.cc)

SET(MAP_REDUCE_SOURCES
        src/views/mapreduce/mapreduce.cc
        src/views/mapreduce/mapreduce_c.cc)

M_MAKE_LEGACY_TEST(couchstore_mapreduce-builtin-test
        ${MAP_REDUCE_SOURCES}
        tests/mapreduce/builtin.cc)

M_MAKE_LEGACY_TEST(couchstore_mapreduce-map-test
        ${MAP_REDUCE_SOURCES}
        tests/mapreduce/map.cc)

M_MAKE_LEGACY_TEST(couchstore_mapreduce-reduce-test
        ${MAP_REDUCE_SOURCES}
        tests/mapreduce/reduce.cc)

cb_add_test_executable(couchstore_testapp
        tests/testapp.cc
        tests/views/tests.cc
        tests/views/collate_json_test.cc
        tests/views/bitmaps.cc
        tests/views/sorted_lists.cc
        tests/views/reductions.cc
        tests/views/keys.cc
        tests/views/values.cc
        tests/views/reducers.cc
        tests/views/cleanup.cc
        tests/views/spatial.cc
        tests/btree_purge/purge_tests.h
        tests/btree_purge/tests.cc
        tests/btree_purge/purge.cc
        $<TARGET_OBJECTS:couchstore_objs>
        $<TARGET_OBJECTS:couchstore_view_objs>)
SET_TARGET_PROPERTIES(couchstore_testapp PROPERTIES
        COMPILE_FLAGS "-DLIBCOUCHSTORE_NO_VISIBILITY=1")
TARGET_INCLUDE_DIRECTORIES(couchstore_testapp
        PRIVATE
        ${CMAKE_CURRENT_BINARY_DIR}/include)
TARGET_LINK_LIBRARIES(couchstore_testapp ${COUCHSTORE_VIEW_LIBS_WITHOUT_GLOBAL_NEW_REPLACEMENT})
cb_enable_unity_build(couchstore_testapp)
SET(COUCHSTORE_GTEST_LIBRARIES GTest::gtest GTest::gtest_main GTest::gmock phosphor)
cb_add_test_executable(couchstore_gtest
        tests/couchstoretest.cc
        tests/documents.cc
        tests/gtest_tests.cc
        tests/test_compact.cc
        tests/test_cxx_util.cc
        tests/test_fileops.cc
        tests/test_seek.cc
        src/node_types.cc
        src/crc32.cc
)
SET_TARGET_PROPERTIES(couchstore_gtest PROPERTIES
        COMPILE_FLAGS "-DLIBCOUCHSTORE_NO_VISIBILITY=1")
TARGET_LINK_LIBRARIES(couchstore_gtest couchstore ${COUCHSTORE_GTEST_LIBRARIES})
cb_enable_unity_build(couchstore_gtest)

cb_add_test_executable(couchstore_internal_gtest
        tests/couchstoretest.cc
        tests/documents.cc
        tests/gtest_internal_tests.cc
        tests/test_fileops.cc
        $<TARGET_OBJECTS:couchstore_objs>)
SET_TARGET_PROPERTIES(couchstore_internal_gtest PROPERTIES
        COMPILE_FLAGS "-DLIBCOUCHSTORE_NO_VISIBILITY=1")
TARGET_INCLUDE_DIRECTORIES(couchstore_internal_gtest
        PRIVATE
        ${CMAKE_CURRENT_BINARY_DIR}/include)

TARGET_LINK_LIBRARIES(couchstore_internal_gtest
        ${COUCHSTORE_GTEST_LIBRARIES}
        ${COUCHSTORE_LIBS})

# This is an object library and can be used for verifying
# FileOpsInterface implementations that wrap other FileOps
# propogate errors correctly.
#
# Example usage can be found in tests/wrapped_fileops_test.cc
ADD_LIBRARY(couchstore_wrapped_fileops_test_framework OBJECT
        tests/test_fileops.cc
        ${COUCHSTORE_FILE_OPS})
SET_TARGET_PROPERTIES(couchstore_wrapped_fileops_test_framework PROPERTIES
        COMPILE_FLAGS "-DLIBCOUCHSTORE_NO_VISIBILITY=1")
TARGET_INCLUDE_DIRECTORIES(couchstore_wrapped_fileops_test_framework
        PRIVATE
        ${CMAKE_CURRENT_BINARY_DIR}/include)
TARGET_LINK_LIBRARIES(couchstore_wrapped_fileops_test_framework
        GTest::gmock cbcrypto platform)

cb_add_test_executable(couchstore_wrapped_fileops_test
        src/iobuffer.cc
        src/crc32.cc
        tests/wrapped_fileops_test.cc
        $<TARGET_OBJECTS:couchstore_wrapped_fileops_test_framework>)
SET_TARGET_PROPERTIES(couchstore_wrapped_fileops_test PROPERTIES
        COMPILE_FLAGS "-DLIBCOUCHSTORE_NO_VISIBILITY=1")
TARGET_INCLUDE_DIRECTORIES(couchstore_wrapped_fileops_test
        PRIVATE
        ${CMAKE_CURRENT_BINARY_DIR}/include)
TARGET_LINK_LIBRARIES(couchstore_wrapped_fileops_test gsl::gsl-lite ${COUCHSTORE_GTEST_LIBRARIES} platform)

ADD_LIBRARY(couchstore_test_fileops OBJECT
        tests/test_fileops.cc)
TARGET_INCLUDE_DIRECTORIES(couchstore_test_fileops
        PRIVATE
        ${CMAKE_CURRENT_BINARY_DIR}/include)
TARGET_LINK_LIBRARIES(couchstore_test_fileops GTest::gmock cbcrypto platform)

if (NOT DEFINED CB_THREADSANITIZER AND NOT DEFINED CB_ADDRESSSANITIZER)
    ADD_TEST(couchstore-file-deduper-test couchstore_file-deduper-test)
    ADD_TEST(couchstore-file-merge-test couchstore_file-merger-test)
    ADD_TEST(couchstore-file-sorter-test couchstore_file-sorter-test)
    ADD_TEST(NAME couchstore-mapreduce-builtin-test COMMAND couchstore_mapreduce-builtin-test ${CMAKE_INSTALL_PREFIX}/bin/)
    ADD_TEST(NAME couchstore-mapreduce-map-test COMMAND couchstore_mapreduce-map-test ${CMAKE_INSTALL_PREFIX}/bin/)
    ADD_TEST(NAME couchstore-mapreduce-reduce-test COMMAND couchstore_mapreduce-reduce-test ${CMAKE_INSTALL_PREFIX}/bin/)
    ADD_TEST(NAME couchstore-testapp COMMAND couchstore_testapp ${CMAKE_INSTALL_PREFIX}/bin/)
endif ()

ADD_TEST(couchstore-gtest couchstore_gtest)
ADD_TEST(couchstore-internal-gtest couchstore_internal_gtest)
ADD_TEST(couchstore-wrapped_fileops-test couchstore_wrapped_fileops_test)

ADD_SUBDIRECTORY(programs)

ENABLE_CODE_COVERAGE_REPORT()
