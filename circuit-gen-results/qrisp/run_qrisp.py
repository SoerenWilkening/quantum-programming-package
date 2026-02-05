import sys
from time import time

from qrisp import QFT, QuantumFloat

n = 1075

if len(sys.argv) > 1:
    n = int(sys.argv[1])


def qft(num):
    t1 = time()
    qpe_res = QuantumFloat(num)
    q = QFT(qpe_res, exec_swap=False)
    return time() - t1


print(qft(n))
