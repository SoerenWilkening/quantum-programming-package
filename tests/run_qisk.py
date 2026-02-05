from time import time

# from qutip_qip.qasm import read_qasm
# qc = read_qasm("../../circuit.qasm")
# print(qc)
import qiskit.qasm3
from qiskit import Aer, QuantumCircuit, execute, transpile

# Use the Aer simulator
simulator = Aer.get_backend("aer_simulator")

read = qiskit.qasm3.load("circuit.qasm")
n = len(read.qubits)
t1 = time()
circuit = QuantumCircuit(n)

circuit.append(read, range(n))
circuit.measure_all()
circuit = transpile(circuit)
print(time() - t1)
print(circuit.num_qubits)
job = execute(circuit, backend=simulator, shots=1024)
result = job.result().get_counts()