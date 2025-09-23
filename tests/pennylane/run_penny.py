import pennylane as qml
from time import time
import sys

try:
    n = int(sys.argv[1])
except:
    n = 20

t1 = time()
# Record the QFT circuit without executing
with qml.tape.QuantumTape() as tape:
    qml.templates.QFT(wires=range(n))

expanded_tape = tape.expand()

print(time() - t1)