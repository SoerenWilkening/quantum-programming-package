namespace QuantumProject {

     open Microsoft.Quantum.Canon;
     open Microsoft.Quantum.Math;
     open Microsoft.Quantum.Convert;

     // Define a gate type: name, targets, optional angle
     newtype Gate = (Name : String, Targets : Int[], Angle : Double);

     operation GenerateQFTData(numQubits : Int) : Gate[] {
         mutable gates = new Gate[0];

         for (j in 0 .. numQubits - 1) {
             set gates += [Gate("H", [j], 0.0)];

             for (k in 2 .. numQubits - j) {
                 // mutable result = 1.0;
                 // for (_ in 1 .. k) {
                 //    set result *= 2.0;
                 // }
                 let k_d = IntAsDouble(k);
                 let angle = 2.0 * 3.141592653589793 / PowD(2.0, k_d);
                 set gates += [Gate("CR", [j, j + k - 1], angle)];
             }
         }

         for (i in 0 .. (numQubits / 2) - 1) {
             set gates += [Gate("SWAP", [i, numQubits - i - 1], 0.0)];
         }

         return gates;
     }
 }

