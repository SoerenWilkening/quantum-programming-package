cmake_minimum_required(VERSION 3.28)
project(CQ_backend_improved C)

set(CMAKE_C_STANDARD 23)
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS}")

# Add the include directory (make sure to use the correct path)
#include_directories(${PROJECT_SOURCE_DIR}/Assembly/include)
#include_directories(${PROJECT_SOURCE_DIR}/Backend/include)

add_executable(CQ_backend_improved main.c
        Backend/src/Integer.c
        Backend/src/QPU.c
        Backend/src/gate.c
        Backend/src/IntegerAddition.c
        Backend/src/IntegerMultiplication.c
        Backend/src/LogicOperations.c
        Backend/src/IntegerComparison.c
        Execution/src/execution.c
        Assembly/src/AssemblyComparison.c
        Assembly/src/AssemblyReader.c
        Assembly/src/AssemblyLogic.c
        Assembly/src/AssemblyArithmetic.c
        Assembly/src/AssemblyBasics.c)

add_executable(bench benchmark/benchmark.c
        Backend/src/Integer.c
        Backend/src/QPU.c
        Backend/src/gate.c
        Backend/src/IntegerAddition.c
        Backend/src/IntegerMultiplication.c
        Backend/src/IntegerComparison.c
        Backend/src/LogicOperations.c
        Execution/src/execution.c
        Assembly/src/AssemblyComparison.c
        Assembly/src/AssemblyReader.c
        Assembly/src/AssemblyLogic.c
        Assembly/src/AssemblyArithmetic.c
        Assembly/src/AssemblyBasics.c
        Assembly/include/AssemblyOperations.h)


target_include_directories(CQ_backend_improved PRIVATE ${PROJECT_SOURCE_DIR}/Assembly/include)
target_include_directories(CQ_backend_improved PRIVATE ${PROJECT_SOURCE_DIR}/Backend/include)
target_include_directories(CQ_backend_improved PRIVATE ${PROJECT_SOURCE_DIR}/Execution/include)
target_include_directories(bench PRIVATE ${PROJECT_SOURCE_DIR}/Assembly/include)
target_include_directories(bench PRIVATE ${PROJECT_SOURCE_DIR}/Backend/include)
target_include_directories(bench PRIVATE ${PROJECT_SOURCE_DIR}/Execution/include)
