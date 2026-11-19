# ESP-IDF project boilerplate. Requires an exported IDF_PATH (ESP-IDF v6.1.x).
# This file was not built in the initial commit of the skeleton: the toolchain
# was not installed on the development machine at that time.
cmake_minimum_required(VERSION 3.22)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
idf_build_set_property(MINIMAL_BUILD ON)
project(af_monitor)
