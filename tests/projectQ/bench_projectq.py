# import subprocess
#
# # sizes = list(range(1, 100, 1))
# sizes = list(range(180, 220, 20))
# sizes += range(600, 2200, 200)
# sizes += list(range(200, 600, 100))
#
#
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