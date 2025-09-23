import subprocess

sizes = list(range(1, 31, 1))
# sizes += list(range(100, 200, 5))
# sizes += list(range(200, 520, 20))
#
# sizes += range(600, 2100, 100)

for s in sizes:
    print(s)
    res = subprocess.run(["/usr/bin/time", "-l", "/Users/sorenwilkening/.pyenv/versions/Solvers/bin/python", "run_aria.py", f"{s}"], capture_output=True, text = True)

    t1 = float(res.stdout)
    mem = int(res.stderr.split("maximum resident set size")[0].split("\n")[-1])
    print(t1, mem)

    with open("aria_qft.csv", "a") as f:
        f.write(f"{s},{t1},{mem},aria\n")
        f.close()