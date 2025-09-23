import subprocess

def run_quipper(s):
    res = subprocess.run(["/usr/bin/time", "-l", "./qft", f"{s}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    t = int(res.stdout.split("t1")[-1].replace(":", "").replace("ps", ""))
    m = int(res.stderr.split("maximum resident set size")[0].split("\n")[-1])
    print(t / 1e12, m)
    return t / 1e12, m

# sizes = list(range(1, 100, 1))
# sizes += list(range(100, 200, 5))
# sizes += list(range(200, 520, 20))
# sizes += range(600, 2100, 100)
#
# for s in sizes:
#     print(s)
#     res = subprocess.run(["/usr/bin/time", "-l", "./qft", f"{s}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
#     t = int(res.stdout.split("t1")[-1].replace(":", "").replace("ps", ""))
#     m = int(res.stderr.split("maximum resident set size")[0].split("\n")[-1])
#     print(t / 1e12, m)
#     with open("quipper_qft_times.csv", "a") as f:
#         f.write(f"{s},{t / 1e12},{m}\n")
#         f.close()