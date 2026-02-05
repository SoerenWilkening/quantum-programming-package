import sys
from time import time

from pytket.circuit import Circuit

try:
    n = int(sys.argv[1])
except:
    n = 5


def build_qft_circuit(n_qubits: int) -> Circuit:
    circ = Circuit(n_qubits, name="$$QFT$$")
    for i in range(n_qubits):
        circ.H(i)
        for j in range(i + 1, n_qubits):
            circ.CU1(1 / 2 ** (j - i), j, i)
    return circ


t1 = time()
circ = build_qft_circuit(n)
print(time() - t1)
