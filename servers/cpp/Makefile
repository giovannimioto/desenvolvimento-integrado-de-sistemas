# Build multiplataforma: Linux e Windows (MSYS2 UCRT64).
CXX        = g++
ARCH_FLAGS ?= -mavx2 -mfma          # use ARCH_FLAGS= caso o CPU nao suporte AVX2/FMA
CXXFLAGS   = -std=c++17 -O3 $(ARCH_FLAGS) -Wall -Wextra -pthread -DEIGEN_DONT_PARALLELIZE
EIGEN_INC ?= $(patsubst -I%,-isystem %,$(shell pkg-config --cflags eigen3 2>/dev/null || echo -I/usr/include/eigen3))
INCLUDES   = $(EIGEN_INC) -Isrc -isystem third_party

ifeq ($(OS),Windows_NT)
  EXE  = .exe
  LIBS = -lws2_32                   # sockets do Windows (cpp-httplib)
endif

BUILD       = build
COMUM       = $(filter-out src/main.cpp,$(wildcard src/*.cpp))   # modulos reaproveitados
HEADERS     = $(wildcard src/*.hpp)
OBJS        = $(patsubst src/%.cpp,$(BUILD)/%.o,$(COMUM))
FERRAMENTAS = $(patsubst ferramentas/%.cpp,$(BUILD)/%$(EXE),$(wildcard ferramentas/*.cpp))

all: $(BUILD)/servidor$(EXE) $(FERRAMENTAS)

$(BUILD)/%.o: src/%.cpp $(HEADERS) | $(BUILD)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $< -o $@

$(BUILD)/servidor$(EXE): src/main.cpp $(OBJS) | $(BUILD)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $^ -o $@ $(LIBS)

$(BUILD)/%$(EXE): ferramentas/%.cpp $(OBJS) | $(BUILD)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $^ -o $@ $(LIBS)

$(BUILD)/testes_unitarios$(EXE): testes/testes_unitarios.cpp $(OBJS) | $(BUILD)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $^ -o $@ $(LIBS)

test: $(BUILD)/testes_unitarios$(EXE)
	./$(BUILD)/testes_unitarios$(EXE)

$(BUILD):
	mkdir -p $(BUILD)

clean:
	rm -rf $(BUILD)

.PHONY: all test clean
