
import os
import subprocess, sys

sizes = list(range(1, 100, 1))
sizes += list(range(100, 200, 5))
sizes += list(range(200, 520, 20))

sizes += range(600, 2100, 100)

for s in sizes:
    print(s)
    os.system(f"cd ../../ && cmake -B build -DINTEGERSIZE={s} >out 2>out")
    os.system("cd ../../ && cmake --build build >out 2>out")
    os.system("cd ../../ && mv build tests/cq")

    res = subprocess.run(["/usr/bin/time", "-l", "./build/CQ_backend_improved"], capture_output=True, text = True)

    os.system("cd ../../ && rm -r tests/cq/build")
    print(res.stdout)
    print(res.stderr)
    _, t2, t1 = map(float, res.stdout.split())
    mem = int(res.stderr.split("maximum resident set size")[0].split("\n")[-1])

    with open("CQ_impr.csv", "a") as f:
        f.write(f"{s},{t1},{mem}\n")
        f.close()

    with open("CQ.csv", "a") as f:
        f.write(f"{s},{t2},{mem}\n")
        f.close()

