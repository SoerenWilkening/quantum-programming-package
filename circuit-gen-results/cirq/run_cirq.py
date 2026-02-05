import sys
from time import time

import cirq
import pandas as pd


def make_qft(qubits):
    """Generator for the QFT on a list of qubits."""
    qreg = list(qubits)
    while len(qreg) > 0:
        q_head = qreg.pop(0)
        yield cirq.H(q_head)
        for i, qubit in enumerate(qreg):
            yield (cirq.CZ ** (1 / 2 ** (i + 1)))(qubit, q_head)


df = pd.DataFrame({"n": [], "t": []})

n = int(sys.argv[1])
gate_set = [cirq.H, cirq.CZPowGate]
# samples = 1
# for n in [256, 512, 1024]:
q = cirq.LineQubit.range(n)
t_tot = 0
# print(n)
# for _ in range(samples):
qc = cirq.Circuit()
t1 = time()
qc += make_qft(q)
t_tot += time() - t1
print(t_tot)
del qc
# df = pd.concat([df, pd.DataFrame({"n": [n], "t": [t_tot]})], ignore_index=True)
#
# df.to_csv("../circ_qft_res.txt")
