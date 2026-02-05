import math
import sys
from time import time

from braket.circuits import Circuit

n = 1500

if len(sys.argv) > 1:
    n = int(sys.argv[1])


def qft(n_qubits: int) -> Circuit:
    circ = Circuit()
    for i in range(n_qubits):
        circ.h(i)
        for j in range(i + 1, n_qubits):
            try:
                angle = math.pi / (2.0 ** (j - i))
            except:
                angle = 0
            circ.cphaseshift(j, i, angle)  # controlled phase rotation
    return circ


# Build a 3-qubit QFT
t1 = time()
qft_circuit = qft(n)
print(time() - t1)
# print(qft_circuit)
