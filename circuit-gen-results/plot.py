"""
optimal speed to construct n-bit qft:
theoretical minimum cycles to store gate in circuit:
 - +1 Target
 - +1 Control (for multi control)
 - +1 Gate (H or P)
 - +1 Gatevalue (if Gate is P)
 - +1 Layer in circuit, where to be applied (find minimum possible layer)
 - +1 adjust Layer after applying
n-bit qft consists of n H Gates (single qubit) and n (n + 1) / 2 - n CP gates (single contol P)
=> cycle count: 4n + 6(n (n + 1) / 2 - n)
"""
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import matplotlib
from matplotlib.patches import Patch

sns.set_theme()
font = {'family': 'serif', 'size': 12}
matplotlib.rc('font', **font)

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = "Times New Roman"
plt.rcParams['mathtext.fontset'] = 'stix'

colors = sns.color_palette("Paired", 20)   # or "hls", "Paired", etc.
colors[0] = (0.12156862745098039, 0.4666666666666667, 0.7058823529411765)
colors[10] = (0.596078431372549, 0.3058823529411765, 0.6392156862745098)
colors[13] = (0. ,0. ,0. )

# colors = plt.cm.tab20.colors  # 20 distinct RGBA tuples
print(colors[3])

markers = [".", "o", "s", "D", "^", "v", "<", ">", "p", "P", "*", "X", "h", "H", "+", "x", "|", "_"]


def optimal_qft(n, cpu_frec=4e9):
    n = np.array(n)
    res = (4 * n + 6 * (n * (n + 1) / 2 - n)) / cpu_frec
    return res


def optimal_mem_qft(n, cpu_frec=4.1e9):
    n = np.array(n)
    res = (4 * n + 6 * (n * (n + 1) / 2 - n) * 2) * 2
    return res


method_name = "QCB"
method_name2 = "QCB improved"

res = pd.read_csv("results.csv")
aria = res[res["meth"] == "aria"]
projectq = res[res["meth"] == "projectq"]
qisk = res[res["meth"] == "qiskit"]
cq_impr = res[res["meth"] == "cq_impr"]
cq = res[res["meth"] == "cq"]
ket = res[res["meth"] == "ket"]
cirq = res[res["meth"] == "cirq"]
amaz = res[res["meth"] == "amazon"]
penny = res[res["meth"] == "pennylane"]
qs = res[res["meth"] == "qsharp"]
pytket = res[res["meth"] == "pytket"]
quipper = res[res["meth"] == "quipper"]
straw = res[res["meth"] == "strawberry"]
qrisp = res[res["meth"] == "qrisp"]
quil = res[res["meth"] == "quil"]

fontsize = 12
every = 1
size = 5
width = 0.75
linewidth = 1.5

f = plt.figure(figsize=(15.11078 / 2.54, 15.11078 / 1.3 / 2.54))
# f = plt.figure(figsize=(510 / 72.27, 4))
plt.plot(cq_impr["n"], optimal_qft(cq_impr["n"]), "--", label="theoretical limit", color=colors[0])
plt.fill_between(cq_impr["n"], 10 * optimal_qft(cq_impr["n"]), 20 * optimal_qft(cq_impr["n"]), label="realistic hardware limit", alpha=0.4, color=colors[0])
plt.plot(cq["n"], cq["t"], "--", label=method_name, color=colors[3], marker = markers[1], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(cq_impr["n"], cq_impr["t"], "--", label=method_name2, color=colors[5], marker = markers[0], markevery=every)
plt.plot(qisk["n"], qisk["t"], "--", label="Qiskit", color=colors[1], marker = markers[2], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(cirq["n"], cirq["t"], "--", label="Cirq", color=colors[4], marker = markers[3], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(qs["n"], qs["t"], "--", label="Q#", color=colors[6], marker = markers[4], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(quipper["n"], quipper["t"], "--", label="Quipper", color=colors[2], marker = markers[5], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(amaz["n"], amaz["t"], "--", label="Amazon-Braket", color=colors[7], marker = markers[6], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(ket["n"], ket["t"], "--", label="Ket", color=colors[8], marker = markers[7], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(penny["n"], penny["t"], "--", label="Pennylane", color=colors[9], marker = markers[8], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(straw["n"], straw["t"], "--", label="Strawberryfields", color=colors[13], marker = markers[12], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(pytket["n"], pytket["t"], "--", label="PyTKet", color=colors[10], marker = markers[9], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(aria["n"], aria["t"], "--", label="AriaQuanta", color=colors[11], marker = markers[10], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(projectq["n"], projectq["t"], "--", label="ProjectQ", color=colors[12], marker = markers[11], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(qrisp["n"], qrisp["t"], "--", label="Qrisp", color="tab:gray", marker = markers[13], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(quil["n"], quil["t"], "--", label="Quil", color="tab:olive", marker = markers[14], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.xlim(0.9, 2100)
# plt.ylim(1e-9, 1000)
plt.xscale('log')
plt.yscale('log')
plt.ylabel('Time $[s]$', fontsize = fontsize)
plt.xlabel('Qubits', fontsize = fontsize)
plt.xticks(fontsize = fontsize)
plt.yticks(fontsize = fontsize)
# Place legend **outside to the right**
# clean legend placement + smaller font
plt.legend(
    ncol=4,
    loc='lower center',
    bbox_to_anchor=(0.5, 1.001),  # just above plot, minimal space
    fontsize=9,
)
# plt.legend(
#     loc='center left',             # anchor legend from left center
#     bbox_to_anchor=(1, 0.5),        # (x, y) position: 1 is just outside the axes on the right
#     fontsize = fontsize,
#     # ncols=2
# )
# plt.subplots_adjust(right=0.9)
plt.tight_layout(pad = 0.)
plt.savefig("time_circuit_generation.pdf")
plt.show()

f = plt.figure(figsize=(15.11078 / 2.54, 15.11078 / 1.3 / 2.54))
# f = plt.figure(figsize=(510 / 72.27, 4))
plt.plot(cq_impr["n"], optimal_mem_qft(cq_impr["n"]), "--", label="theoretical limit", color=colors[0])
plt.plot(cq_impr["n"], cq_impr["m"], "--", label=method_name, color=colors[5], marker = markers[0], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(cq["n"], cq["m"], "--", label=method_name2, color=colors[3], marker = markers[1], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(qisk["n"], qisk["m"], "--", label="Qiskit", color=colors[1], marker = markers[2], markevery=every)
plt.plot(cirq["n"], cirq["m"], "--", label="Cirq", color=colors[4], marker = markers[3], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(qs["n"], qs["m"], "--", label="Q#", color=colors[6], marker = markers[4], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(quipper["n"], quipper["m"], "--", label="Quipper", color=colors[2], marker = markers[5], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(amaz["n"], amaz["m"], "--", label="Amazon-Braket", color=colors[7], marker = markers[6], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(ket["n"], ket["m"], "--", label="Ket", color=colors[8], marker = markers[7], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(penny["n"], penny["m"], "--", label="Pennylane", color=colors[9], marker = markers[8], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(straw["n"], straw["m"], "--", label="Strawberryfields", color=colors[13], marker = markers[12], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(pytket["n"], pytket["m"], "--", label="PyTKet", color=colors[10], marker = markers[9], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(aria["n"], aria["m"], "--", label="AriaQuanta", color=colors[11], marker = markers[10], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(projectq["n"], projectq["m"], "--", label="ProjectQ", color=colors[12], marker = markers[11], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(qrisp["n"], qrisp["m"], "--", label="Qrisp", color="tab:gray", marker = markers[13], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
plt.plot(quil["n"], quil["m"], "--", label="Quil", color="tab:olive", marker = markers[14], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
# plt.xlim(1, 11)
# plt.ylim(1e-9, 1000)
plt.xscale('log')
plt.yscale('log')
plt.xticks(fontsize = fontsize)
plt.yticks(fontsize = fontsize)
plt.ylabel('Memory $[$bytes$]$', fontsize=fontsize)
plt.xlabel('Qubits', fontsize=fontsize)
plt.legend(
    ncol=4,
    loc='lower center',
    bbox_to_anchor=(0.5, 1.001),  # just above plot, minimal space
    fontsize=9,
)
# plt.legend(
#     loc='center left',             # anchor legend from left center
#     bbox_to_anchor=(1, 0.5),        # (x, y) position: 1 is just outside the axes on the right
#     fontsize = fontsize,
#     # ncols=2
# )
# plt.subplots_adjust(right=0.76)
plt.tight_layout(pad = 0.)
plt.savefig("memory_circuit_generation.pdf")
plt.show()
