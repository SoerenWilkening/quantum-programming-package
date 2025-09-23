using System;
using System.IO;
using System.Diagnostics;
using System.Globalization;
using QuantumProject;
using Microsoft.Quantum.Simulation.Simulators; // Needed for QuantumSimulator

class Program
{
    static void Main(string[] args)
    {
        long numQubits = long.Parse(args[0]);
//        int counter = 0;
//        for (long numQubits = 1; numQubits <= 2048; numQubits *= 2){

            Stopwatch stopwatch = new Stopwatch();
            stopwatch.Start();
            // Must provide a simulator as the first argument
            using var sim = new QuantumSimulator();

            // Generate the QFT gate sequence
            var qftCircuit = QuantumProject.GenerateQFTData.Run(sim, numQubits).Result;


            stopwatch.Stop();

            string filePath = "qsharp_qft_times.csv";

            long ticks = stopwatch.ElapsedTicks;
            double nanoseconds = (ticks * 1_000_000_000.0) / Stopwatch.Frequency;

//             using (StreamWriter writer = new StreamWriter(filePath, append: true))
//             {
//                 writer.Write($"{numQubits},{(nanoseconds / 1_000_000_000).ToString("F10", CultureInfo.InvariantCulture)}");
//             }
            // counter += 1;
            Console.WriteLine($"{(nanoseconds/ 1_000_000_000).ToString("F10", CultureInfo.InvariantCulture)}");
//        }


    }
}
