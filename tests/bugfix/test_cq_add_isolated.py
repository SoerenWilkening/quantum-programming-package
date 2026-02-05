"""Isolated CQ_add diagnostic test.

Tests qint(0, width=4) += 1 in a fresh process with NO prior quantum operations.
If this passes (result=1), the CQ_add algorithm is correct and failures in
multi-test runs are caused by BUG-05 cache pollution.
If this fails (result!=1), there is a genuine convention bug in CQ_add.
"""

from verify_helpers import format_failure_message

import quantum_language as ql


def test_cq_add_0_plus_1_isolated(verify_circuit):
    """Isolated test: qint(0) += 1 should equal 1.

    This test is designed to run in a fresh process with no prior
    quantum operations to diagnose whether CQ_add failures are
    caused by cache pollution (BUG-05) or a genuine algorithm bug.
    """

    def circuit_builder():
        a = ql.qint(0, width=4)
        a += 1
        return 1

    actual, expected = verify_circuit(circuit_builder, width=4)
    assert actual == expected, format_failure_message("add", [0, 1], 4, expected, actual)
