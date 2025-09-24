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
font = {'family': 'serif', 'size': 18}
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


def optimal_mem_qft(n, cpu_frec=4e9):
    n = np.array(n)
    res = (4 * n + 6 * (n * (n + 1) / 2 - n)) * 8
    return res


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

fontsize = 12. / 0.8
every = 1
size = 5
width = 0.75
linewidth = 1.5
# , markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth
#
# Example plot
fig, ax = plt.subplots()
line2 = ax.fill_between(cq_impr["n"], 10 * optimal_qft(cq_impr["n"]), 20 * optimal_qft(cq_impr["n"]), label="realistic hardware limit", alpha=0.4, color=colors[0])
line1, = ax.plot(cq_impr["n"], optimal_qft(cq_impr["n"]), "--", label="theoretical limit", color=colors[1])
line3, = ax.plot(cq["n"], cq["t"], "--", label="CQ", color=colors[3], marker = markers[1], markevery=every)
line4, = ax.plot(cq_impr["n"], cq_impr["t"], "--", label="CQ improved", color=colors[5], marker = markers[0], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
line5, = ax.plot(qisk["n"], qisk["t"], "--", label="Qiskit", color=colors[1], marker = markers[2], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
line6, = ax.plot(cirq["n"], cirq["t"], "--", label="Cirq", color=colors[4], marker = markers[3], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
line7, = ax.plot(qs["n"], qs["t"], "--", label="Q#", color=colors[6], marker = markers[4], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
line8, = ax.plot(quipper["n"], quipper["t"], "--", label="Quipper", color=colors[2], marker = markers[5], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
line9, = ax.plot(amaz["n"], amaz["t"], "--", label="Amazon-Braket", color=colors[7], marker = markers[6], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
line10, = ax.plot(ket["n"], ket["t"], "--", label="Ket", color=colors[8], marker = markers[7], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
line11, = ax.plot(penny["n"], penny["t"], "--", label="Pennylane", color=colors[9], marker = markers[8], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
line15, = ax.plot(straw["n"], straw["t"], "--", label="Strawberryfields", color=colors[13], marker = markers[12], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
line12, = ax.plot(pytket["n"], pytket["t"], "--", label="PyTKet", color=colors[10], marker = markers[9], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
line13, = ax.plot(aria["n"], aria["t"], "--", label="AriaQuanta", color=colors[11], marker = markers[10], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
line14, = ax.plot(projectq["n"], projectq["t"], "--", label="ProjectQ", color=colors[12], marker = markers[11], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)

ax.set_title("Main Plot (no legend here)")

proxy_fill1 = Patch(facecolor=colors[0], alpha=0.5, label="realistic hardware limit")

hand = [
	line1,
	proxy_fill1,
	line3,
	line4,
	line5,
	line6,
	line7,
	line8,
	line9,
	line10,
	line11,
	line12,
	line13,
	line14,
	line15,
]

# Create a separate figure just for the legend
fig_legend = plt.figure(figsize=(9.25,1.35))
fig_legend.legend(
	handles=hand,
	labels=[line.get_label() for line in hand],
	loc='center',
	fontsize=fontsize,
	ncol=4
)

# Remove axes in legend figure
for ax in fig_legend.axes:
	ax.remove()

fig_legend.tight_layout()
plt.savefig("legend.pdf")
plt.show()


f = plt.figure(figsize=(8, 5.5))
plt.plot(cq_impr["n"], optimal_qft(cq_impr["n"]), "--", label="theoretical limit", color=colors[0])
plt.fill_between(cq_impr["n"], 10 * optimal_qft(cq_impr["n"]), 20 * optimal_qft(cq_impr["n"]), label="realistic hardware limit", alpha=0.4, color=colors[0])
plt.plot(cq_impr["n"], cq_impr["t"], "--", label="CQ improved", color=colors[5], marker = markers[0], markevery=every)
plt.plot(cq["n"], cq["t"], "--", label="CQ", color=colors[3], marker = markers[1], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
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
plt.xlim(0.9, 2100)
# plt.ylim(1e-9, 1000)
plt.xscale('log')
plt.yscale('log')
plt.ylabel('Time $[s]$', fontsize = fontsize)
plt.xlabel('Qubits', fontsize = fontsize)
plt.xticks(fontsize = fontsize)
plt.yticks(fontsize = fontsize)
plt.tight_layout(pad = 0.2)
plt.savefig("time_circuit_generation.pdf")
plt.show()

f = plt.figure(figsize=(8, 5.5))
plt.plot(cq_impr["n"], optimal_mem_qft(cq_impr["n"]), "--", label="theoretical limit", color=colors[0])
plt.plot(cq_impr["n"], cq_impr["m"], "--", label="CQ", color=colors[5], marker = markers[0], markevery=every, markersize=size, markeredgewidth=width, linewidth=linewidth)
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
# plt.xlim(1, 11)
# plt.ylim(1e-9, 1000)
plt.xscale('log')
plt.yscale('log')
plt.xticks(fontsize = fontsize)
plt.yticks(fontsize = fontsize)
plt.ylabel('Memory $[$bytes$]$', fontsize=fontsize)
plt.xlabel('Qubits', fontsize=fontsize)
plt.tight_layout(pad = 0.2)
plt.savefig("memory_circuit_generation.pdf")
plt.show()










# import numpy as np
# import matplotlib.pyplot as plt
#
# # Suppose we want 10 evenly spaced points between 1 and 1000
# x = np.unique(np.round(np.logspace(np.log10(1), np.log10(2000), num=50)).astype(int))
# y = x ** 2
#
# plt.figure()
# plt.plot(x, y, '.-')
# plt.xscale('log')
# # plt.yscale('log')
# # plt.xticks(x, [f"{int(v)}" for v in x])  # label with integers (approx)
# plt.show()
