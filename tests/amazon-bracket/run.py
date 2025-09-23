import os, subprocess

# sizes = list(range(1, 100, 1))
# sizes = list(range(100, 200, 5))
# sizes += list(range(200, 520, 20))

# sizes = range(600, 1100, 100)
sizes = range(1500, 2100, 500)

for s in sizes:
    print(s)
    res = subprocess.run(["/usr/bin/time", "-l", "/Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum Programming Language/Quantum_Assembly/.venv/bin/python3", "bracket_run.py", f"{s}"], capture_output=True, text = True)

    t1 = float(res.stdout)
    mem = int(res.stderr.split("maximum resident set size")[0].split("\n")[-1])
    print(t1, mem)

    with open("amazon.csv", "a") as f:
        f.write(f"{s},{t1},{mem}\n")
        f.close()