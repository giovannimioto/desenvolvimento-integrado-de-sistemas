CXX      = g++
CXXFLAGS = -std=c++17 -O3 -march=native -Wall -pthread
INCLUDES = -IC:/msys64/ucrt64/include/eigen3
SRC      = $(wildcard src/*.cpp)
TARGET   = servidor

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $^ -o $@

clean:
	del /Q $(TARGET).exe

.PHONY: all clean