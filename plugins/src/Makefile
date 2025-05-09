FF_ROOT = /usr/local/lib/ff++/4.10
CXXFLAGS = -std=c++11 -fPIC -I$(FF_ROOT)/include -I/usr/include/freefem -I/usr/include/suitesparse
LDFLAGS = -shared -L$(FF_ROOT)/lib -lfreefem

all: mmap-semaphore.so

mmap-semaphore.so: mmap-semaphore.cpp
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS)

clean:
	rm -f *.so *.o

.PHONY: all clean 