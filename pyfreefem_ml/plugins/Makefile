# Makefile for FreeFEM++ mmap-semaphore plugin

# FreeFEM include path
FF_INCLUDEPATH = /usr/local/lib/ff++/4.10/include

# Compiler and flags
CXX = g++
CXXFLAGS = -std=c++11 -fPIC -shared -O3 -DNDEBUG
INCLUDES = -I$(FF_INCLUDEPATH)

# Target shared library
TARGET = mmap-semaphore.so

# Source file
SRC = mmap-semaphore.cpp

# FreeFEM plugin directory
PLUGIN_DIR = $(HOME)/.ff++/lib

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $@ $<

install: $(TARGET)
	mkdir -p $(PLUGIN_DIR)
	cp $(TARGET) $(PLUGIN_DIR)/
	@echo "Plugin installed to $(PLUGIN_DIR)/$(TARGET)"

clean:
	rm -f $(TARGET)

uninstall:
	rm -f $(PLUGIN_DIR)/$(TARGET)

.PHONY: all install clean uninstall 