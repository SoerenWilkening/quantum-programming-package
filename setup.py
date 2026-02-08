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

from build_preprocessor import preprocess_all

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
    # Hot path migrations (Phase 60)
    os.path.join(PROJECT_ROOT, "c_backend", "src", "hot_path_mul.c"),
    os.path.join(PROJECT_ROOT, "c_backend", "src", "hot_path_add.c"),
    os.path.join(PROJECT_ROOT, "c_backend", "src", "hot_path_xor.c"),
    # Hardcoded addition sequences: 16 per-width files + unified dispatch
    *[
        os.path.join(PROJECT_ROOT, "c_backend", "src", "sequences", f"add_seq_{i}.c")
        for i in range(1, 17)
    ],
    os.path.join(PROJECT_ROOT, "c_backend", "src", "sequences", "add_seq_dispatch.c"),
]

compiler_args = ["-O3", "-pthread"]  # Removed -flto due to GCC LTO bug

# Profiling build mode - enables Cython function-level profiling
profiling_directives = {}
if os.environ.get("QUANTUM_PROFILE"):
    profiling_directives = {
        "profile": True,
        "linetrace": True,
    }
    compiler_args.append("-DCYTHON_TRACE=1")

# Debug build mode - re-enables all safety checks for debugging
debug_directives = {}
if os.environ.get("CYTHON_DEBUG"):
    debug_directives = {
        "boundscheck": True,
        "wraparound": True,
        "initializedcheck": True,
    }

# src/ directory is at project root, not in python-backend
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

include_dirs = [
    os.path.join(PROJECT_ROOT, "c_backend", "include"),
    SRC_DIR,  # CRITICAL: Allows cimport to find .pxd files in package
]

# Preprocess .pyx files that use include directives (Cython 3.x workaround)
# This inlines .pxi content into *_preprocessed.pyx files before compilation.
preprocessed_map = {}  # original stem -> preprocessed path
for orig, preprocessed in preprocess_all(Path(SRC_DIR) / "quantum_language"):
    preprocessed_map[orig.stem] = str(preprocessed)

# Auto-discover all .pyx files in package
extensions = []
for pyx_file in glob.glob(os.path.join(SRC_DIR, "quantum_language", "**", "*.pyx"), recursive=True):
    pyx_path = Path(pyx_file)
    # Skip preprocessed files from discovery (they're used as sources below)
    if pyx_path.stem.endswith("_preprocessed"):
        continue
    # Convert path to module name:
    # src/quantum_language/qint.pyx -> quantum_language.qint
    # src/quantum_language/state/qpu.pyx -> quantum_language.state.qpu
    module_name = pyx_path.relative_to(SRC_DIR).with_suffix("").as_posix().replace("/", ".")

    # Use preprocessed source if this file had include directives
    source = preprocessed_map.get(pyx_path.stem, pyx_file)

    extensions.append(
        Extension(
            name=module_name,
            sources=[source] + c_sources,
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
            **profiling_directives,
            **debug_directives,
        },
    ),
    # Include .pxd and .py files for installed package (e.g. __init__.py wrappers)
    package_data={
        "quantum_language": ["*.pxd", "*.py"],
        "quantum_language.state": ["*.pxd", "*.py"],
    },
    install_requires=[
        "Pillow>=9.0",
    ],
    extras_require={
        "verification": ["qiskit>=1.0"],
        "profiling": [
            "line-profiler>=5.0.0",
            "snakeviz>=2.2.2",
            "pytest-benchmark>=5.2.3",
        ],
    },
    python_requires=">=3.11",
)
