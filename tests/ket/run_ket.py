from time import time
from ket import Process, QFT, adj
import numpy as np

import os, psutil
import sys
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