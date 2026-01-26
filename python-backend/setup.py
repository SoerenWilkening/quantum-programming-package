import os

from Cython.Build import cythonize
from setuptools import Extension, setup

compiler_args = ["-O3", "-flto", "-pthread"]

sources_circuit = [
    os.path.join("quantum_language.pyx"),
    os.path.join("..", "Backend", "src", "QPU.c"),
    os.path.join("..", "Backend", "src", "qubit_allocator.c"),
    os.path.join("..", "Backend", "src", "circuit_allocations.c"),
    os.path.join("..", "Backend", "src", "ciruict_outputs.c"),
    os.path.join("..", "Backend", "src", "gate.c"),
    os.path.join("..", "Backend", "src", "Integer.c"),
    os.path.join("..", "Backend", "src", "IntegerAddition.c"),
    os.path.join("..", "Backend", "src", "IntegerComparison.c"),
    os.path.join("..", "Backend", "src", "IntegerMultiplication.c"),
    os.path.join("..", "Backend", "src", "LogicOperations.c"),
    os.path.join("..", "Execution", "src", "execution.c"),
]

extensions = [
    Extension(
        name="quantum_language",
        sources=sources_circuit,
        language="c",
        extra_compile_args=compiler_args,
        include_dirs=[
            os.path.join("..", "Backend", "include"),
            os.path.join("..", "Execution", "include"),
        ],
    )
]

setup(
    ext_modules=cythonize(
        extensions,
        language_level="3",
    )
)
