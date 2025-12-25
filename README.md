# Speed-oriented quantum circuit backend

Repository containing a quantum circuit generator written in C.
Test on up to 2000 qubit QFTs demonstrate speed advantage over current software backends

Clone repository and compile the code with the following command:

```bash
mkdir build && cd build
cmake ..
cmake --build .
```

TODO:
- integration into higher order language
- increase stability for larger circuits
- include more rudimentary operations
- Extend intermediate assembly like intruction set
- inlcude more circuit optimizations
