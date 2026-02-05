import sys
from time import time

from ket import QFT, Process

sys.setrecursionlimit(3000)

try:
    n = int(sys.argv[1])
except:
    n = 20

p = Process(num_qubits=n)
a = p.alloc(n)
t1 = time()
QFT(a, do_swap=False)
t = time() - t1
print(t)
