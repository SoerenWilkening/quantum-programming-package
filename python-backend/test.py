from quantum_language import qint, qbool

A = qint(classical = False)
B = qint(classical = False)
c = qbool(classical = False)



with c:
	A += B
# 	with d:
# 		3 + B
# with ~c:
# 	pass


A.print_circuit()
# A.print_circuit()