cmake_minimum_required(VERSION 3.15)
project(stream_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(pybind11 REQUIRED)

pybind11_add_module(stream_native
    stream_native.cpp
    stream_native.hpp
)

target_include_directories(stream_native PRIVATE .)
