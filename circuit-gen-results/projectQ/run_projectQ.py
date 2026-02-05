import sys
from time import time

from projectq import MainEngine
from projectq.backends import ResourceCounter
from projectq.ops import QFT
from projectq.setups import linear

try:
    n = int(sys.argv[1])
except:
    n = 512

t = time()
compiler_engines = linear.get_engine_list(
    num_qubits=n, one_qubit_gates="any", two_qubit_gates="any"
)
resource_counter = ResourceCounter()
eng = MainEngine(backend=resource_counter, engine_list=compiler_engines)
qureg = eng.allocate_qureg(n)
QFT | qureg
eng.flush()
print(time() - t)
