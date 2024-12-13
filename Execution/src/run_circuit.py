from qutip import tensor, basis, Qobj
import os
import numpy as np

# from qutip_qip.qasm import read_qasm
# qc = read_qasm("../../circuit.qasm")
# print(qc)

import qiskit.qasm3
from qiskit import QuantumCircuit, transpile

from qiskit import Aer
from qiskit import execute

# Use the Aer simulator
simulator = Aer.get_backend('aer_simulator')

read = qiskit.qasm3.load("/Users/sorenwilkening/Desktop/Quantum_Assembly/circuit.qasm")
n = len(read.qubits)
circuit = QuantumCircuit(n)

circuit.append(read, range(n))
circuit.measure_all()
circuit = transpile(circuit)
# print(circuit)

job = execute(circuit, backend=simulator, shots=1024)
result = job.result().get_counts()
for i in result:
    i = i[::-1]
    print(i[0], end = " ")
    i = i[1:]
    print(i[:4], i[4:8], i[8:12])