# Q# circuit builder is compiled. It stores the runtime. The python script executes it and stores the peak memory

import os
import sys
import subprocess

def run_qsharp(s):
    result = subprocess.run(["/usr/bin/time", "-l", "dotnet", "bin/Debug/net6.0/QuantumProject.dll", str(s)], capture_output=True, text=True)
    t = float(result.stdout.split("\n")[0])
    mem = int(result.stderr.split("maximum resident set size")[0].split("\n")[1])
    return t, mem

# run_qsharp(100)