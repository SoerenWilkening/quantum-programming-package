#!/usr/bin/env python3
"""Build configuration for quantum_language package.

Builds multiple Cython extensions from src/quantum_language/*.pyx files.
Each .pyx becomes a separate compiled extension module.
"""

import glob
import os
from pathlib import Path

from Cython.Build import cythonize
from setuptools import Extension, find_packages, setup

# Shared C sources from Backend
c_sources = [
    os.path.join("..", "Backend", "src", "QPU.c"),
    os.path.join("..", "Backend", "src", "optimizer.c"),
    os.path.join("..", "Backend", "src", "qubit_allocator.c"),
    os.path.join("..", "Backend", "src", "circuit_allocations.c"),
    os.path.join("..", "Backend", "src", "circuit_output.c"),
    os.path.join("..", "Backend", "src", "circuit_stats.c"),
    os.path.join("..", "Backend", "src", "circuit_optimizer.c"),
    os.path.join("..", "Backend", "src", "gate.c"),
    os.path.join("..", "Backend", "src", "Integer.c"),
    os.path.join("..", "Backend", "src", "IntegerAddition.c"),
    os.path.join("..", "Backend", "src", "IntegerComparison.c"),
    os.path.join("..", "Backend", "src", "IntegerMultiplication.c"),
    os.path.join("..", "Backend", "src", "LogicOperations.c"),
    os.path.join("..", "Execution", "src", "execution.c"),
]

compiler_args = ["-O3", "-flto", "-pthread"]

include_dirs = [
    os.path.join("..", "Backend", "include"),
    os.path.join("..", "Execution", "include"),
    ".",  # CRITICAL: Allows cimport to find .pxd files in package
    "src",  # Also check src directory for imports
]

# Auto-discover all .pyx files in package
extensions = []
for pyx_file in glob.glob("src/quantum_language/**/*.pyx", recursive=True):
    # Convert path to module name:
    # src/quantum_language/qint.pyx -> quantum_language.qint
    # src/quantum_language/state/qpu.pyx -> quantum_language.state.qpu
    module_name = Path(pyx_file).relative_to("src").with_suffix("").as_posix().replace("/", ".")

    extensions.append(
        Extension(
            name=module_name,
            sources=[pyx_file] + c_sources,
            language="c",
            extra_compile_args=compiler_args,
            include_dirs=include_dirs,
        )
    )

# Fallback: if no .pyx files found in src/, try old structure
if not extensions:
    print("Warning: No .pyx files found in src/. Using legacy single-file build.")
    # Keep original build for backward compatibility during transition
    extensions = [
        Extension(
            name="quantum_language",
            sources=["quantum_language_preprocessed.pyx"] + c_sources,
            language="c",
            extra_compile_args=compiler_args,
            include_dirs=include_dirs[:2],  # Original include dirs
        )
    ]

setup(
    name="quantum-assembly",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    ext_modules=cythonize(
        extensions,
        language_level="3",
        compiler_directives={
            "embedsignature": True,  # Preserves docstrings in compiled modules
        },
    ),
    # Include .pxd files for potential cimport by external projects
    package_data={
        "quantum_language": ["*.pxd"],
        "quantum_language.state": ["*.pxd"],
    },
    python_requires=">=3.11",
)
