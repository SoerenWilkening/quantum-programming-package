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

# Shared C sources from c_backend
# Project root is the current directory
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

c_sources = [
    os.path.join(PROJECT_ROOT, "c_backend", "src", "QPU.c"),
    os.path.join(PROJECT_ROOT, "c_backend", "src", "optimizer.c"),
    os.path.join(PROJECT_ROOT, "c_backend", "src", "qubit_allocator.c"),
    os.path.join(PROJECT_ROOT, "c_backend", "src", "circuit_allocations.c"),
    os.path.join(PROJECT_ROOT, "c_backend", "src", "circuit_output.c"),
    os.path.join(PROJECT_ROOT, "c_backend", "src", "circuit_stats.c"),
    os.path.join(PROJECT_ROOT, "c_backend", "src", "circuit_optimizer.c"),
    os.path.join(PROJECT_ROOT, "c_backend", "src", "gate.c"),
    os.path.join(PROJECT_ROOT, "c_backend", "src", "Integer.c"),
    os.path.join(PROJECT_ROOT, "c_backend", "src", "IntegerAddition.c"),
    os.path.join(PROJECT_ROOT, "c_backend", "src", "IntegerComparison.c"),
    os.path.join(PROJECT_ROOT, "c_backend", "src", "IntegerMultiplication.c"),
    os.path.join(PROJECT_ROOT, "c_backend", "src", "LogicOperations.c"),
    os.path.join(PROJECT_ROOT, "c_backend", "src", "execution.c"),
]

compiler_args = ["-O3", "-flto", "-pthread"]

# src/ directory is at project root, not in python-backend
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

include_dirs = [
    os.path.join(PROJECT_ROOT, "c_backend", "include"),
    SRC_DIR,  # CRITICAL: Allows cimport to find .pxd files in package
]

# Auto-discover all .pyx files in package
extensions = []
for pyx_file in glob.glob(os.path.join(SRC_DIR, "quantum_language", "**", "*.pyx"), recursive=True):
    # Convert path to module name:
    # src/quantum_language/qint.pyx -> quantum_language.qint
    # src/quantum_language/state/qpu.pyx -> quantum_language.state.qpu
    module_name = Path(pyx_file).relative_to(SRC_DIR).with_suffix("").as_posix().replace("/", ".")

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
            include_dirs=include_dirs[:1],  # Original include dir (c_backend only)
        )
    ]

setup(
    name="quantum-assembly",
    version="0.1.0",
    packages=find_packages(where=SRC_DIR),
    package_dir={"": SRC_DIR},
    ext_modules=cythonize(
        extensions,
        language_level="3",
        compiler_directives={
            "embedsignature": True,  # Preserves docstrings in compiled modules
        },
    ),
    # Include .pxd and .py files for installed package (e.g. __init__.py wrappers)
    package_data={
        "quantum_language": ["*.pxd", "*.py"],
        "quantum_language.state": ["*.pxd", "*.py"],
    },
    python_requires=">=3.11",
)
