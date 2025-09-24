import strawberryfields as sf
from strawberryfields import ops
import numpy as np
import time
import sys

def qft_circuit(n_qubits: int):
    prog = sf.Program(n_qubits)

    with prog.context as q:
        for i in range(n_qubits):
            # Hadamard equivalent (50:50 beam splitter + phase shift)
            ops.Rgate(np.pi/2) | q[i]

            # Controlled phase rotations (approximate with beamsplitters + Rgates)
            for j in range(i+1, n_qubits):
                try:
                    angle = np.pi / (2 ** (j - i))
                except:
                    angle = 1e-15
                ops.Rgate(angle) | q[j]

        # Swap qubits to reverse order (optional but standard in QFT)
        for i in range(n_qubits // 2):
            ops.BSgate(np.pi/4) | (q[i], q[n_qubits - i - 1])

    return prog

# 🔥 Benchmark the circuit generation time
try:
    n = int(sys.argv[1])
except:
    n = 50

start = time.time()
prog = qft_circuit(n)
end = time.time()
print(f"{end - start}")
