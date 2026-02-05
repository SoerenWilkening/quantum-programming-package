import subprocess


def extract(res):
    t1 = float(res.stdout)
    mem = int(res.stderr.split("maximum resident set size")[0].split("\n")[-1])
    return t1, mem


def store(name, s, t1, mem):
    with open("results.csv", "a") as f:
        f.write(f"{s},{t1},{mem},{name}\n")
        f.close()


def run_quil(s):
    res = subprocess.run(
        ["/usr/bin/time", "-l", "venv/bin/python", "run_quil.py", f"{s}"],
        capture_output=True,
        text=True,
    )
    t, mem = extract(res)
    store("quil", s, t, mem)


def run_amazon(s):
    res = subprocess.run(
        ["/usr/bin/time", "-l", "venv/bin/python3", "amazon-braket/run_braket.py", f"{s}"],
        capture_output=True,
        text=True,
    )
    t, mem = extract(res)
    store("amazon", s, t, mem)


def run_aria(s):
    res = subprocess.run(
        ["/usr/bin/time", "-l", "venv/bin/python", "AriaQuanta/run_aria.py", f"{s}"],
        capture_output=True,
        text=True,
    )
    t, mem = extract(res)
    store("aria", s, t, mem)


def run_cirq(s):
    res = subprocess.run(
        ["/usr/bin/time", "-l", "venv/bin/python", "cirq/rin_cirq.py", f"{s}"],
        capture_output=True,
        text=True,
    )
    t, mem = extract(res)
    store("cirq", s, t, mem)


def run_cq(s):
    res = subprocess.run(
        ["/usr/bin/time", "-l", "../build/CQ_backend_improved", f"{s}", "0"],
        capture_output=True,
        text=True,
    )  # improved
    res2 = subprocess.run(
        ["/usr/bin/time", "-l", "../build/CQ_backend_improved", f"{s}", "1"],
        capture_output=True,
        text=True,
    )  # current
    t1 = float(res.stdout)
    t2 = float(res2.stdout)
    mem = int(res.stderr.split("maximum resident set size")[0].split("\n")[-1])
    mem2 = int(res2.stderr.split("maximum resident set size")[0].split("\n")[-1])
    # print(t1, t2, mem)
    store("cq_impr", s, t1, mem)
    store("cq", s, t2, mem2)


def run_ket(s):
    res = subprocess.run(
        ["/usr/bin/time", "-l", "venv/bin/python", "ket/run_ket.py", f"{s}"],
        capture_output=True,
        text=True,
    )
    t, mem = extract(res)
    store("ket", s, t, mem)


def run_pennylane(s):
    res = subprocess.run(
        ["/usr/bin/time", "-l", "venv/bin/python", "pennylane/run_penny.py", f"{s}"],
        capture_output=True,
        text=True,
    )
    t, mem = extract(res)
    store("pennylane", s, t, mem)


def run_projectq(s):
    res = subprocess.run(
        ["/usr/bin/time", "-l", "venv/bin/python", "projectQ/run_projectq.py", f"{s}"],
        capture_output=True,
        text=True,
    )
    t, mem = extract(res)
    store("projectq", s, t, mem)


def run_pytket(s):
    res = subprocess.run(
        ["/usr/bin/time", "-l", "venv/bin/python", "pytket/run_pytket.py", f"{s}"],
        capture_output=True,
        text=True,
    )
    t, mem = extract(res)
    store("pytket", s, t, mem)


def run_qiskit(s):
    res = subprocess.run(
        ["/usr/bin/time", "-l", "venv/bin/python", "qiskit/run_qiskit.py", f"{s}"],
        capture_output=True,
        text=True,
    )
    t, mem = extract(res)
    store("qiskit", s, t, mem)


def run_qrips(s):
    res = subprocess.run(
        ["/usr/bin/time", "-l", "venv/bin/python", "qrisp/run_qrisp.py", f"{s}"],
        capture_output=True,
        text=True,
    )
    t, mem = extract(res)
    store("qrisp", s, t, mem)


def run_qsharp(s):
    result = subprocess.run(
        ["/usr/bin/time", "-l", "dotnet", "qsharp/bin/Debug/net6.0/qsharp.dll", str(s)],
        capture_output=True,
        text=True,
    )
    t = float(result.stdout.split("\n")[0])
    mem = int(result.stderr.split("maximum resident set size")[0].split("\n")[1])
    store("qsharp", s, t, mem)


def run_quipper(s):
    res = subprocess.run(
        ["/usr/bin/time", "-l", "./quipper/qft", f"{s}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    t = int(res.stdout.split("t1")[-1].replace(":", "").replace("ps", ""))
    m = int(res.stderr.split("maximum resident set size")[0].split("\n")[-1])
    store("quipper", s, t / 1e12, m)


def run_straw(s):
    res = subprocess.run(
        ["/usr/bin/time", "-l", "venv/bin/python", "strawberry_fields/run_straw.py", f"{s}"],
        capture_output=True,
        text=True,
    )
    t, mem = extract(res)
    store("strawberry", s, t, mem)


import numpy as np

# Suppose we want 10 evenly spaced points between 1 and 2000
x = np.unique(np.round(np.logspace(np.log10(1), np.log10(2000), num=50)).astype(int))

print(x)
for s in x:
    print(s)
    print("Aria")
    run_aria(s)
    if s <= 495:
        run_projectq(s)
    print("Qiskit")
    run_qiskit(s)
    print("CQ")
    run_cq(s)
    print("KET")
    run_ket(s)
    print("Cirq")
    run_cirq(s)
    print("Amazon")
    run_amazon(s)
    print("penny")
    run_pennylane(s)
    print("qsharp")
    if s <= 1000:
        run_qsharp(s)
    print("qrisp")
    run_qrips(s)
    print("pytket")
    run_pytket(s)
    print("quipper")
    run_quipper(s)  # for your own sanity, don't do it
    print("strawberry fields")
    run_straw(s)
    print("Quil")
    run_quil(s)
