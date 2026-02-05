import sys
from time import time

import pandas as pd
from qiskit import QuantumCircuit
from qiskit.circuit.library import QFT
from qiskit.compiler import transpile

df = pd.DataFrame({"n": [], "t": []})

n = int(sys.argv[1])
t_tot = 0
qc = QuantumCircuit(n)
t1 = time()
qft = QFT(n, do_swaps=False)
qc.append(qft, range(n))
qc = transpile(qc, basis_gates=["h", "cp"])
t_tot += time() - t1
print(t_tot)
# del qc
# df = pd.concat([df, pd.DataFrame({"n": [n], "t": [t_tot]})], ignore_index=True)

# df.to_csv("qiskit_qft_res.csv")

# n = 64
# qc = QuantumCircuit(n)
# qft = QFT(n, do_swaps=False)
# qft_inv = QFT(n, do_swaps=False, inverse= True)
# qc.append(qft, range(n))
# # qc.append(qft_inv, range(n))
# qc = transpile(qc, basis_gates=["h", "cp"])
# # print(qc)
# print(qc.depth())
