CXX ?= g++
CXXFLAGS ?= -std=c++11 -O2 -Wall -Wextra -Werror

test_sequence: test_sequence.cpp ../can_flipper/*.h
	$(CXX) $(CXXFLAGS) -o $@ test_sequence.cpp -lm

run: test_sequence
	./test_sequence sequence_nominal.csv

.PHONY: run
.DEFAULT_GOAL := run
