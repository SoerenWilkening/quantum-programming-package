import subprocess

sizes = list(range(1, 100, 1))
sizes += list(range(100, 200, 5))
sizes += list(range(200, 520, 20))

sizes += range(600, 2100, 100)

for s in sizes:
    print(s)
    res = subprocess.run(["/usr/bin/time", "-l", "/Users/sorenwilkening/.pyenv/versions/Solvers/bin/python", "runket.py", f"{s}"], capture_output=True, text = True)

    # print(res)
    t1 = float(res.stdout)
    mem = int(res.stderr.split("maximum resident set size")[0].split("\n")[-1])
    # print(t1, mem)

    with open("ket_qft.csv", "a") as f:
        f.write(f"{s},{t1},{mem},ket\n")
        f.close()