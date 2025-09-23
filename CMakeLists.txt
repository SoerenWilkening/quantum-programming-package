cmake_minimum_required(VERSION 3.28)
project(Quantum_assembly C)

set(CMAKE_C_STANDARD 23)
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS}")


add_executable(CQ_backend_improved main.c
        Backend/src/Integer.c
        Backend/src/QPU.c
        Backend/src/gate.c
        Backend/include/definition.h
        Backend/src/IntegerAddition.c
        Backend/src/IntegerMultiplication.c
        Backend/src/LogicOperations.c
        Backend/src/IntegerComparison.c
        Execution/src/execution.c
        Assembly/src/AssemblyComparison.c
        Assembly/src/AssemblyReader.c
        Assembly/src/AssemblyLogic.c
        Assembly/src/AssemblyBasics.c
        Assembly/src/AssemblyIntegerAddition.c
        Assembly/src/AssemblyIntegerMultiplication.c
        Assembly/src/AssemblyIntegerDivision.c)
set(INTEGERSIZE 800 CACHE STRING "Size of integer")
target_compile_definitions(CQ_backend_improved PRIVATE INTEGERSIZE=${INTEGERSIZE})
add_compile_definitions(CQ_backend_improved PRIVATE INTEGERSIZE=${INTEGERSIZE})
target_compile_options(CQ_backend_improved PRIVATE -O3)

#add_executable(bench benchmark/benchmark.c
#        Backend/src/Integer.c
#        Backend/src/QPU.c
#        Backend/src/gate.c
#        Backend/src/IntegerAddition.c
#        Backend/src/IntegerMultiplication.c
#        Backend/src/IntegerComparison.c
#        Backend/src/LogicOperations.c
#        Execution/src/execution.c
#        Assembly/src/AssemblyComparison.c
#        Assembly/src/AssemblyReader.c
#        Assembly/src/AssemblyLogic.c
#        Assembly/src/AssemblyBasics.c
#        Assembly/include/AssemblyOperations.h
#        Assembly/src/AssemblyIntegerAddition.c
#        Assembly/src/AssemblyIntegerMultiplication.c
#        Assembly/src/AssemblyIntegerDivision.c)


target_include_directories(CQ_backend_improved PRIVATE ${PROJECT_SOURCE_DIR}/Assembly/include)
target_include_directories(CQ_backend_improved PRIVATE ${PROJECT_SOURCE_DIR}/Backend/include)
target_include_directories(CQ_backend_improved PRIVATE ${PROJECT_SOURCE_DIR}/Execution/include)
#target_include_directories(bench PRIVATE ${PROJECT_SOURCE_DIR}/Assembly/include)
#target_include_directories(bench PRIVATE ${PROJECT_SOURCE_DIR}/Backend/include)
#target_include_directories(bench PRIVATE ${PROJECT_SOURCE_DIR}/Execution/include)
