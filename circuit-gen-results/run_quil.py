import sys
from time import time

from pyquil import Program
from pyquil.gates import CPHASE, H

n = 1500

if len(sys.argv) > 1:
    n = int(sys.argv[1])


def build_qft(n):
    t1 = time()
    p = Program()
    for i in range(n):
        p += H(i)
        for j in range(i + 1, n):
            p += CPHASE(1 / 2 ** (j - i), j, i)

    return time() - t1


print(build_qft(n))
