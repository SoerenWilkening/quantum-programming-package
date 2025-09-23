from time import time
from ket import Process, QFT
import numpy as np

import os, psutil
import sys
sys.setrecursionlimit(3000)

try:
    n = int(sys.argv[1])
except:
    n = 30

p = Process(num_qubits=n)
a = p.alloc(n)
t1 = time()
QFT(a)
t = time() - t1
print(t)