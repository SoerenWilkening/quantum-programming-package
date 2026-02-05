# External Integrations

**Analysis Date:** 2026-01-25

## APIs & External Services

**Quantum Circuit Execution:**
- Qiskit Aer (IBM Quantum) - High-performance quantum circuit simulator
  - SDK/Client: `qiskit.Aer` module
  - Purpose: Quantum circuit simulation and validation

- Qiskit QASM3 - OpenQASM 3.0 format parsing and loading
  - SDK/Client: `qiskit.qasm3` module
  - Purpose: Load and parse `.qasm` circuit files in `Execution/src/run_circuit.py`

- Qiskit IBM Quantum Provider - Cloud quantum computer access
  - SDK/Client: `qiskit_ibmq_provider` 0.20.2
  - Auth: Credentials required (not configured in codebase)
  - Status: Installed but not actively used in visible code

**Comparative Benchmarking:**
- Circuit generation testing against multiple quantum frameworks:
  - Qiskit (`circuit-gen-results/qiskit/`)
  - Cirq (Google) (`circuit-gen-results/cirq/`)
  - Amazon Braket (`circuit-gen-results/amazon-braket/`)
  - PennyLane (`circuit-gen-results/pennylane/`)
  - ProjectQ (`circuit-gen-results/projectQ/`)
  - PyTKET (`circuit-gen-results/pytket/`)
  - Qrisp (`circuit-gen-results/qrisp/`)
  - Quipper (`circuit-gen-results/quipper/`)
  - Q# / Azure Quantum (`circuit-gen-results/qsharp/`)
  - StrawberryFields (`circuit-gen-results/strawberry_fields/`)
  - Ket (`circuit-gen-results/ket/`)
  - AriaQuanta (`circuit-gen-results/AriaQuanta/`)

## Data Storage

**Databases:**
- Not used

**File Storage:**
- Local filesystem only
  - Circuit files: `circuit.qasm`, `assembly.pqsm`
  - Benchmark results: `circuit-gen-results/results.csv`
  - Performance data: `circuit-gen-results/memory_circuit_generation.pdf`, `circuit-gen-results/time_circuit_generation.pdf`

**Caching:**
- Not implemented

## Authentication & Identity

**Auth Provider:**
- None - No authentication system in codebase
- Qiskit IBM cloud access credentials would be required at runtime but not integrated

## Monitoring & Observability

**Error Tracking:**
- Not detected

**Logs:**
- Console output via `printf()` in C code
- Circuit printing via `print_circuit()` function in `Backend/src/ciruict_outputs.c`
- Python timing measurements in `Execution/src/run_circuit.py`

## CI/CD & Deployment

**Hosting:**
- Not deployed - Research/development repository

**CI Pipeline:**
- Not detected

## Environment Configuration

**Required env vars:**
- Not required - No environment variables detected in codebase

**Secrets location:**
- None - No secrets management configured
- IBM Quantum credentials would be required for cloud access but handled externally

## Webhooks & Callbacks

**Incoming:**
- Not detected

**Outgoing:**
- Not detected

## Quantum Circuit File Formats

**Input Formats:**
- OpenQASM 3.0 (`.qasm` files) - Parsed via Qiskit QASM3
- Internal Assembly Format (`.pqsm` - Pqsm Assembly)
- C language definitions in `Backend/include/definition.h`

**Output Formats:**
- Circuit visualization (ASCII art format) - Example in `main.c` comments showing circuit topology
- QASM format output (implicit via generation)
- Quantum state measurements via Qiskit

## Benchmarking Framework

**Test Data Location:**
- `circuit-gen-results/` directory
  - Performance results: `results.csv`
  - Analysis plots: `plot.py`
  - PDF reports: `time_circuit_generation.pdf`, `memory_circuit_generation.pdf`

**Test Script:**
- `circuit-gen-results/run.py` - Main benchmark execution script
- `circuit-gen-results/run_quil.py` - Quil-specific quantum language benchmarking

## Performance Profiling

**Timing:**
- Clock-based measurement in `main.c` using `clock()` CLOCKS_PER_SEC
- Python timing in `run_circuit.py` using `time.time()`

**Memory:**
- Manual allocation tracking via `malloc()` and `free()`
- Circuit state managed in `Backend/src/circuit_allocations.c`

---

*Integration audit: 2026-01-25*
