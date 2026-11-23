CXX ?= g++
CXXFLAGS ?= -O3 -Wall -Wextra -shared -std=c++17 -fPIC
PY_INCLUDES := $(shell python3 -m pybind11 --includes)
EXT_SUFFIX := $(shell python3-config --extension-suffix)
TARGET := src/native/stream_native$(EXT_SUFFIX)

all: $(TARGET)

$(TARGET): src/native/stream_native.cpp src/native/stream_native.hpp
	$(CXX) $(CXXFLAGS) $(PY_INCLUDES) src/native/stream_native.cpp -o $(TARGET)

clean:
	rm -f src/native/*.so
	rm -rf build dist

test: all
	python3 -m unittest discover -s tests -v

run: all
	python3 src/main.py

package: all
	bash scripts/build_linux.sh

.PHONY: all clean test run package
