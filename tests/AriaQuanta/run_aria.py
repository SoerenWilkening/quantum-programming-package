from AriaQuanta.aqc.gatelibrary import H, CP
from AriaQuanta.aqc.circuit import Circuit
from time import time
from AriaQuanta.aqc.visualization import CircuitVisualizer
import sys
try:
    n = int(sys.argv[1])
except:
    n = 10

def build_qft_circuit(n_qubits: int) -> Circuit:
    qc = Circuit(n_qubits)         # Create a 2-qubit quantum circuit
    for i in range(n_qubits):
        qc | H(i)
        for j in range(i + 1, n_qubits):
            qc | CP(1 / 2 ** (j - i), j, i)
    return qc

t1 = time()
qc = build_qft_circuit(n)
print(time() - t1)