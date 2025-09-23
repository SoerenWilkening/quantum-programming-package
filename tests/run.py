import subprocess

def run_quipper(s):
    res = subprocess.run(["/usr/bin/time", "-l", "./qft", f"{s}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    t = int(res.stdout.split("t1")[-1].replace(":", "").replace("ps", ""))
    m = int(res.stderr.split("maximum resident set size")[0].split("\n")[-1])
    print(t / 1e12, m)
    return t / 1e12, m



# def run_projectq(s):
#     return subprocess.run(["/usr/bin/time", "-l", "/Users/sorenwilkening/.pyenv/versions/Solvers/bin/python", "run_projectq.py", f"{s}"], capture_output=True, text = True)

# for s in sizes:
#     print(s)
#     res = subprocess.run(["/usr/bin/time", "-l", "/Users/sorenwilkening/.pyenv/versions/Solvers/bin/python", "run_projectq.py", f"{s}"], capture_output=True, text = True)
#
#     t1 = float(res.stdout)
#     mem = int(res.stderr.split("maximum resident set size")[0].split("\n")[-1])
#     print(t1, mem)
#
#     with open("project_qft.csv", "a") as f:
#         f.write(f"{s},{t1},{mem},projectq\n")
#         f.close()