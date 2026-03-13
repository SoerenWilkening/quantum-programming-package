#!/usr/bin/env python3
"""Build configuration for quantum_language package.

Builds multiple Cython extensions from src/quantum_language/*.pyx files.
Each .pyx becomes a separate compiled extension module.
"""

import glob
import os
import sys
from pathlib import Path

# Ensure project root is in path for build_preprocessor import
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from Cython.Build import cythonize  # noqa: E402
from setuptools import Extension, find_packages, setup  # noqa: E402

from build_preprocessor import preprocess_all  # noqa: E402

# Shared C sources from c_backend (relative paths for setuptools compatibility)
C_BACKEND = "c_backend/src"
C_SEQ = "c_backend/src/sequences"

c_sources = [
    f"{C_BACKEND}/optimizer.c",
    f"{C_BACKEND}/qubit_allocator.c",
    f"{C_BACKEND}/circuit_allocations.c",
    f"{C_BACKEND}/circuit_output.c",
    f"{C_BACKEND}/circuit_stats.c",
    f"{C_BACKEND}/circuit_optimizer.c",
    f"{C_BACKEND}/gate.c",
    f"{C_BACKEND}/Integer.c",
    f"{C_BACKEND}/IntegerAddition.c",
    f"{C_BACKEND}/IntegerComparison.c",
    f"{C_BACKEND}/IntegerMultiplication.c",
    f"{C_BACKEND}/LogicOperations.c",
    f"{C_BACKEND}/execution.c",
    # Hot path migrations (Phase 60, 74 split)
    f"{C_BACKEND}/hot_path_mul.c",
    # Toffoli arithmetic (Phase 66, 68, 74 split)
    f"{C_BACKEND}/ToffoliAdditionHelpers.c",
    f"{C_BACKEND}/ToffoliAdditionCDKM.c",
    f"{C_BACKEND}/ToffoliAdditionCLA.c",
    f"{C_BACKEND}/ToffoliMultiplication.c",
    f"{C_BACKEND}/ToffoliDivision.c",
    f"{C_BACKEND}/ToffoliModReduce.c",
    # Hardcoded Toffoli addition sequences: 8 per-width files + dispatch
    *[f"{C_SEQ}/toffoli_add_seq_{i}.c" for i in range(1, 9)],
    f"{C_SEQ}/toffoli_add_seq_dispatch.c",
    # Hardcoded MCX-decomposed Toffoli cQQ sequences: 8 per-width files + dispatch
    *[f"{C_SEQ}/toffoli_decomp_seq_{i}.c" for i in range(1, 9)],
    f"{C_SEQ}/toffoli_decomp_seq_dispatch.c",
    # Hardcoded Toffoli CQ increment sequences: 8 per-width files
    *[f"{C_SEQ}/toffoli_cq_inc_seq_{i}.c" for i in range(1, 9)],
    # Hardcoded Clifford+T CDKM sequences: 32 per-width files + dispatch (Phase 75)
    *[f"{C_SEQ}/toffoli_clifft_qq_{i}.c" for i in range(1, 9)],
    *[f"{C_SEQ}/toffoli_clifft_cqq_{i}.c" for i in range(1, 9)],
    *[f"{C_SEQ}/toffoli_clifft_cq_inc_{i}.c" for i in range(1, 9)],
    *[f"{C_SEQ}/toffoli_clifft_ccq_inc_{i}.c" for i in range(1, 9)],
    f"{C_SEQ}/toffoli_clifft_cdkm_dispatch.c",
    # Hardcoded Clifford+T BK CLA sequences: 28 per-width files + dispatch (Phase 75)
    *[f"{C_SEQ}/toffoli_clifft_cla_qq_{i}.c" for i in range(2, 9)],
    *[f"{C_SEQ}/toffoli_clifft_cla_cqq_{i}.c" for i in range(2, 9)],
    *[f"{C_SEQ}/toffoli_clifft_cla_cq_inc_{i}.c" for i in range(2, 9)],
    *[f"{C_SEQ}/toffoli_clifft_cla_ccq_inc_{i}.c" for i in range(2, 9)],
    f"{C_SEQ}/toffoli_clifft_cla_dispatch.c",
    # Hardcoded QFT addition sequences: 16 per-width files + unified dispatch
    *[f"{C_SEQ}/add_seq_{i}.c" for i in range(1, 17)],
    f"{C_SEQ}/add_seq_dispatch.c",
]

# Build type: Release by default (optimized for size), Debug via BUILD_TYPE=Debug
# Profiling/coverage modes force Debug-like flags (incompatible with stripping)
build_type = os.environ.get("BUILD_TYPE", "Release")
is_release = build_type.lower() == "release"

# Override: profiling/coverage modes need debug-like flags (no stripping, no gc-sections)
if os.environ.get("QUANTUM_PROFILE") or os.environ.get("QUANTUM_COVERAGE"):
    is_release = False

if is_release:
    # SIZE-01: -ffunction-sections + -fdata-sections enable per-function/data section GC
    # SIZE-03: -Os for size optimization (benchmarked: within 15% of -O3)
    # Removed -flto due to GCC LTO bug
    compiler_args = ["-Os", "-ffunction-sections", "-fdata-sections", "-pthread"]
    if sys.platform == "darwin":
        # macOS linker uses -dead_strip instead of --gc-sections
        # SIZE-02: -Wl,-x strips local symbols (macOS equivalent of -s)
        linker_args = ["-Wl,-dead_strip", "-Wl,-x"]
    else:
        # SIZE-01: -Wl,--gc-sections removes unreferenced sections
        # SIZE-02: -s strips all symbols at link time
        linker_args = ["-Wl,--gc-sections", "-s"]
else:
    # Debug/development: keep -O3 for speed, no stripping
    # Removed -flto due to GCC LTO bug
    compiler_args = ["-O3", "-pthread"]
    linker_args = []

# Profiling build mode - enables Cython function-level profiling
profiling_directives = {}
if os.environ.get("QUANTUM_PROFILE"):
    profiling_directives = {
        "profile": True,
        "linetrace": True,
    }
    compiler_args.append("-DCYTHON_TRACE=1")

# Coverage build mode - enables Cython linetrace and C gcov instrumentation
coverage_directives = {}
if os.environ.get("QUANTUM_COVERAGE"):
    coverage_directives = {
        "linetrace": True,
    }
    compiler_args.append("-DCYTHON_TRACE=1")
    # Disable sys.monitoring path: Cython 3.2.x generates an undeclared
    # __Pyx_MonitoringEventTypes_CyGen_count in coroutine-bearing modules on
    # Python 3.13+.  The older cProfile-based trace mechanism still works.
    compiler_args.append("-DCYTHON_USE_SYS_MONITORING=0")
    compiler_args.append("--coverage")
    linker_args.append("--coverage")  # Link gcov runtime for coverage symbols

# Debug build mode - re-enables all safety checks for debugging
debug_directives = {}
if os.environ.get("CYTHON_DEBUG"):
    debug_directives = {
        "boundscheck": True,
        "wraparound": True,
        "initializedcheck": True,
    }

# src/ directory is at project root, not in python-backend
SRC_DIR = "src"

include_dirs = [
    "c_backend/include",
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
            extra_link_args=linker_args,
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
    name="quantum_language",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    ext_modules=cythonize(
        extensions,
        language_level="3",
        compiler_directives={
            "embedsignature": True,  # Preserves docstrings in compiled modules
            **profiling_directives,
            **coverage_directives,
            **debug_directives,
        },
    ),
    # Include .pxd and .py files for installed package (e.g. __init__.py wrappers)
    package_data={
        "quantum_language": ["*.pxd", "*.py"],
        "quantum_language.state": ["*.pxd", "*.py"],
    },
    python_requires=">=3.11",
)
