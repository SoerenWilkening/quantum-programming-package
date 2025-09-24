import subprocess, os

def extract(res):
    t1 = float(res.stdout)
    mem = int(res.stderr.split("maximum resident set size")[0].split("\n")[-1])
    return t1, mem

def store(name, s, t1, mem):
    with open("results.csv", "a") as f:
        f.write(f"{s},{t1},{mem},{name}\n")
        f.close()

def run_amazon(s):
    res = subprocess.run(["/usr/bin/time", "-l", "/Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum Programming Language/Quantum_Assembly/.venv/bin/python3", "amazon-braket/run_braket.py", f"{s}"], capture_output=True, text = True)
    t, mem = extract(res)
    store("amazon", s, t, mem)

def run_aria(s):
    res = subprocess.run(["/usr/bin/time", "-l", "/Users/sorenwilkening/.pyenv/versions/Solvers/bin/python", "AriaQuanta/run_aria.py", f"{s}"], capture_output=True, text = True)
    t, mem = extract(res)
    store("aria", s, t, mem)

def run_cirq(s):
    res = subprocess.run(["/usr/bin/time", "-l", "/Users/sorenwilkening/.pyenv/versions/3.11.9/envs/qiskit/bin/python3", "cirq/rin_cirq.py", f"{s}"], capture_output=True, text = True)
    t, mem = extract(res)
    store("cirq", s, t, mem)

def run_cq(s):
    os.system(f"cd ../ && cmake -B build -DINTEGERSIZE={s} >out 2>out")
    os.system("cd ../ && cmake --build build >out 2>out")
    os.system("cd ../ && mv build tests/cq")

    res = subprocess.run(["/usr/bin/time", "-l", "./cq/build/CQ_backend_improved"], capture_output=True, text = True)

    os.system("cd ../ && rm -r tests/cq/build")
    _, t2, t1 = map(float, res.stdout.split())
    mem = int(res.stderr.split("maximum resident set size")[0].split("\n")[-1])
    store("cq_impr", s, t1, mem)
    store("cq", s, t2, mem)
    # return t1, t2, mem

def run_ket(s):
    res = subprocess.run(["/usr/bin/time", "-l", "/Users/sorenwilkening/.pyenv/versions/Solvers/bin/python", "ket/run_ket.py", f"{s}"], capture_output=True, text = True)
    t, mem = extract(res)
    store("ket", s, t, mem)

def run_pennylane(s):
    res = subprocess.run(["/usr/bin/time", "-l", "/Users/sorenwilkening/.pyenv/versions/Solvers/bin/python", "pennylane/run_penny.py", f"{s}"], capture_output=True, text = True)
    t, mem = extract(res)
    store("pennylane", s, t, mem)

def run_projectq(s):
    res = subprocess.run(["/usr/bin/time", "-l", "/Users/sorenwilkening/.pyenv/versions/Solvers/bin/python", "projectQ/run_projectq.py", f"{s}"], capture_output=True, text = True)
    t, mem = extract(res)
    store("projectq", s, t, mem)

def run_pytket(s):
    res =  subprocess.run(["/usr/bin/time", "-l", "/Users/sorenwilkening/.pyenv/versions/Solvers/bin/python", "pytket/run_pytket.py", f"{s}"], capture_output=True, text = True)
    t, mem = extract(res)
    store("pytket", s, t, mem)

def run_qiskit(s):
    res = subprocess.run(["/usr/bin/time", "-l", "/Users/sorenwilkening/.pyenv/versions/3.11.9/envs/qiskit/bin/python3", "qiskit/run_qiskit.py", f"{s}"], capture_output=True, text = True)
    t, mem = extract(res)
    store("qiskit", s, t, mem)

def run_qsharp(s):
    result = subprocess.run(["/usr/bin/time", "-l", "dotnet", "qsharp/bin/Debug/net6.0/qsharp.dll", str(s)], capture_output=True, text=True)
    t = float(result.stdout.split("\n")[0])
    mem = int(result.stderr.split("maximum resident set size")[0].split("\n")[1])
    store("qsharp", s, t, mem)

def run_quipper(s):
    res = subprocess.run(["/usr/bin/time", "-l", "./quipper/qft", f"{s}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    t = int(res.stdout.split("t1")[-1].replace(":", "").replace("ps", ""))
    m = int(res.stderr.split("maximum resident set size")[0].split("\n")[-1])
    store("quipper", s, t / 1e12, m)
    # return t / 1e12, m

def run_straw(s):
    res = subprocess.run(["/usr/bin/time", "-l", "/Users/sorenwilkening/.pyenv/versions/Solvers/bin/python", "strawberry_fields/run_straw.py", f"{s}"], capture_output=True, text = True)
    t, mem = extract(res)
    store("strawberry", s, t, mem)

import numpy as np
import os

# Suppose we want 10 evenly spaced points between 1 and 1000
x = np.unique(np.round(np.logspace(np.log10(1), np.log10(2000), num=50)).astype(int))
print(x)
# for s in x[x >= 1075]:
for s in [266, 311, 363]:
    print(s)
    # if s <= 30: run_aria(s)
    if s <= 331: run_projectq(s)
    # run_qiskit(s)
    # run_cq(s)
    # run_ket(s)
    # run_cirq(s)
    # run_amazon(s)
    # run_pennylane(s)
    # if s <= 1000: run_qsharp(s)
    # run_pytket(s)
    # run_quipper(s)
    # run_straw(s)
