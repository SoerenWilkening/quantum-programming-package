cmake_minimum_required(VERSION 3.28)
project(CQ_backend_improved C)

set(CMAKE_C_STANDARD 23)

add_executable(CQ_backend_improved main.c
        src/Integer.c
        src/QPU.c
        src/gate.c
        src/IntegerAddition.c
        src/IntegerMultiplication.c
        src/AssemblyOperations.c
        src/LogicOperations.c
        src/IntegerComparison.c
        src/IntegerComparison.h)

add_executable(bench benchmark/benchmark.c
        src/Integer.c
        src/QPU.c
        src/gate.c
        src/IntegerAddition.c
        src/IntegerMultiplication.c
        src/AssemblyOperations.c
        src/LogicOperations.c
        src/IntegerComparison.c
        src/IntegerComparison.h)

