cmake_minimum_required(VERSION 3.28)
project(Quantum_Assembly C)

set(CMAKE_C_STANDARD 23)
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -O3")


add_executable(CQ_backend_improved main.c
        c_backend/src/Integer.c
        c_backend/src/QPU.c
        c_backend/src/gate.c
        c_backend/include/definition.h
        c_backend/src/IntegerAddition.c
        c_backend/src/IntegerMultiplication.c
        c_backend/src/LogicOperations.c
        c_backend/src/IntegerComparison.c
        c_backend/src/execution.c
        Assembly/src/AssemblyComparison.c
        Assembly/src/AssemblyReader.c
        Assembly/src/AssemblyLogic.c
        Assembly/src/AssemblyBasics.c
        Assembly/src/AssemblyIntegerAddition.c
        Assembly/src/AssemblyIntegerMultiplication.c
        Assembly/src/AssemblyIntegerDivision.c
        c_backend/src/circuit_allocations.c
        c_backend/src/ciruict_outputs.c
        c_backend/src/qubit_allocator.c)

target_compile_options(CQ_backend_improved PRIVATE -O3)


target_include_directories(CQ_backend_improved PRIVATE ${PROJECT_SOURCE_DIR}/Assembly/include)
target_include_directories(CQ_backend_improved PRIVATE ${PROJECT_SOURCE_DIR}/c_backend/include)
