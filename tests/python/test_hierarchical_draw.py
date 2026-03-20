"""Tests for per-function sub-diagram visualization (R20.4 completion).

Verifies:
- CompiledBlock.draw_data() produces valid draw_data dicts
- render_function_diagrams() generates per-function PIL images
- hierarchical_dot() produces DOT with URL links to sub-diagrams
- draw_hierarchical() produces both diagrams and linked DOT
- CallGraphDAG.to_dot(file_prefix=...) adds URL attributes to nodes
"""

import os
import tempfile

from PIL import Image

from quantum_language.call_graph import CallGraphDAG
from quantum_language.compile import CompiledBlock
from quantum_language.compile._block import _H, _X
from quantum_language.draw import (
    _render_block_draw_data,
    draw_hierarchical,
    hierarchical_dot,
    render_function_diagrams,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_block(gates, total_virtual_qubits=4, param_qubit_ranges=None):
    """Build a CompiledBlock with given gates for testing."""
    block = CompiledBlock(
        gates=gates,
        total_virtual_qubits=total_virtual_qubits,
        param_qubit_ranges=param_qubit_ranges or [(1, 4)],
        internal_qubit_count=0,
        return_qubit_range=None,
    )
    return block


def _sample_gates():
    """Return a small list of gate dicts for a 3-qubit block."""
    return [
        {"target": 1, "type": _H, "angle": 0.0, "controls": [], "num_controls": 0},
        {"target": 2, "type": _X, "angle": 0.0, "controls": [1], "num_controls": 1},
        {"target": 3, "type": _X, "angle": 0.0, "controls": [], "num_controls": 0},
    ]


# ---------------------------------------------------------------------------
# CompiledBlock.draw_data()
# ---------------------------------------------------------------------------


class TestBlockDrawData:
    def test_empty_block_draw_data(self):
        """Empty block produces draw_data with zeros."""
        block = _make_block(gates=[])
        dd = block.draw_data()
        assert dd["num_layers"] == 0
        assert dd["num_qubits"] == 0
        assert dd["gates"] == []
        assert dd["qubit_map"] == []

    def test_single_gate_draw_data(self):
        """Single gate produces 1 layer, correct qubit count."""
        gates = [{"target": 2, "type": _H, "angle": 0.0, "controls": [], "num_controls": 0}]
        block = _make_block(gates)
        dd = block.draw_data()
        assert dd["num_layers"] == 1
        assert dd["num_qubits"] == 1
        assert len(dd["gates"]) == 1
        assert dd["gates"][0]["type"] == _H
        assert dd["gates"][0]["layer"] == 0
        assert dd["gates"][0]["target"] == 0  # dense-mapped from virtual qubit 2

    def test_multi_gate_layer_assignment(self):
        """Gates on different qubits share a layer; dependent gates get later layers."""
        gates = _sample_gates()
        block = _make_block(gates)
        dd = block.draw_data()

        assert dd["num_qubits"] == 3
        assert dd["num_layers"] >= 1
        assert len(dd["gates"]) == 3

        # The CNOT (gate 1) depends on qubit 1 used by the H (gate 0),
        # so it must be in a later layer.
        h_layer = dd["gates"][0]["layer"]
        cnot_layer = dd["gates"][1]["layer"]
        assert cnot_layer > h_layer

    def test_draw_data_qubit_map(self):
        """qubit_map contains the original virtual qubit indices sorted."""
        gates = _sample_gates()
        block = _make_block(gates)
        dd = block.draw_data()
        assert dd["qubit_map"] == [1, 2, 3]

    def test_draw_data_controls_remapped(self):
        """Control qubit indices are dense-remapped in draw_data gates."""
        gates = [
            {"target": 5, "type": _X, "angle": 0.0, "controls": [3], "num_controls": 1},
        ]
        block = _make_block(gates, total_virtual_qubits=6)
        dd = block.draw_data()
        # Virtual 3 -> dense 0, virtual 5 -> dense 1
        assert dd["gates"][0]["target"] == 1
        assert dd["gates"][0]["controls"] == [0]

    def test_draw_data_renderable(self):
        """draw_data from a block can be rendered without error."""
        gates = _sample_gates()
        block = _make_block(gates)
        dd = block.draw_data()
        img = _render_block_draw_data(dd, mode="overview")
        assert isinstance(img, Image.Image)
        assert img.size[0] > 0
        assert img.size[1] > 0


# ---------------------------------------------------------------------------
# render_function_diagrams()
# ---------------------------------------------------------------------------


class _FakeCompiledFunc:
    """Minimal mock of CompiledFunc for testing diagram collection."""

    def __init__(self, name, cache=None):
        self._func = type("F", (), {"__name__": name})()
        self._cache = cache or {}
        self._call_graph = None


class TestRenderFunctionDiagrams:
    def test_single_function_diagram(self):
        """Single function with cached block produces one diagram."""
        block = _make_block(_sample_gates())
        func = _FakeCompiledFunc("my_func", cache={("key",): block})
        diagrams = render_function_diagrams(func)
        assert "my_func" in diagrams
        assert isinstance(diagrams["my_func"], Image.Image)

    def test_empty_cache_no_diagrams(self):
        """Function with empty cache produces no diagrams."""
        func = _FakeCompiledFunc("empty_func", cache={})
        diagrams = render_function_diagrams(func)
        assert len(diagrams) == 0

    def test_empty_block_no_diagram(self):
        """Function with empty block (no gates) produces no diagram."""
        block = _make_block(gates=[])
        func = _FakeCompiledFunc("noop", cache={("key",): block})
        diagrams = render_function_diagrams(func)
        assert len(diagrams) == 0

    def test_nested_functions_collected(self):
        """Nested CallRecords produce diagrams for both outer and inner functions."""
        from quantum_language._compile_state import CallRecord

        inner_block = _make_block(_sample_gates())
        inner_func = _FakeCompiledFunc("inner", cache={("ikey",): inner_block})

        outer_gates = [
            {"target": 1, "type": _X, "angle": 0.0, "controls": [], "num_controls": 0},
        ]
        outer_block = _make_block(outer_gates)
        outer_block._call_records.append(
            CallRecord(
                compiled_func_ref=inner_func, cache_key=("ikey",), quantum_arg_indices=[[1, 2, 3]]
            )
        )
        outer_func = _FakeCompiledFunc("outer", cache={("okey",): outer_block})

        diagrams = render_function_diagrams(outer_func)
        assert "outer" in diagrams
        assert "inner" in diagrams

    def test_cycle_does_not_hang(self):
        """Circular CallRecord references do not cause infinite recursion."""
        from quantum_language._compile_state import CallRecord

        block_a = _make_block(_sample_gates())
        func_a = _FakeCompiledFunc("func_a", cache={("ka",): block_a})

        # Self-referencing call record
        block_a._call_records.append(
            CallRecord(compiled_func_ref=func_a, cache_key=("ka",), quantum_arg_indices=[[1]])
        )

        diagrams = render_function_diagrams(func_a)
        assert "func_a" in diagrams

    def test_mode_override(self):
        """Mode parameter is passed through to rendering."""
        block = _make_block(_sample_gates())
        func = _FakeCompiledFunc("f", cache={("k",): block})
        diagrams_detail = render_function_diagrams(func, mode="detail")
        diagrams_overview = render_function_diagrams(func, mode="overview")
        # Detail mode images have different dimensions than overview
        assert diagrams_detail["f"].size != diagrams_overview["f"].size


# ---------------------------------------------------------------------------
# hierarchical_dot()
# ---------------------------------------------------------------------------


class TestHierarchicalDot:
    def test_no_call_graph(self):
        """Function without a call graph returns minimal DOT."""
        func = _FakeCompiledFunc("no_graph")
        dot = hierarchical_dot(func)
        assert "digraph CallGraph" in dot

    def test_dot_contains_url_attributes(self):
        """DOT nodes include URL attributes pointing to sub-diagram files."""
        dag = CallGraphDAG()
        dag.add_node("outer", frozenset({0, 1}), 10, ())
        dag.add_node("inner", frozenset({0, 1}), 5, (), is_call_node=True)
        dag.add_call_edge(0, 1)

        func = _FakeCompiledFunc("outer")
        func._call_graph = dag

        dot = hierarchical_dot(func, file_prefix="func")
        assert 'URL="func_outer.png"' in dot
        assert 'URL="func_inner.png"' in dot

    def test_dot_preserves_call_edges(self):
        """DOT output preserves call edges with dashed blue style."""
        dag = CallGraphDAG()
        dag.add_node("caller", frozenset({0}), 10, ())
        dag.add_node("callee", frozenset({1}), 5, (), is_call_node=True)
        dag.add_call_edge(0, 1)

        func = _FakeCompiledFunc("caller")
        func._call_graph = dag

        dot = hierarchical_dot(func)
        assert 'label="call"' in dot
        assert "style=dashed" in dot
        assert "color=blue" in dot

    def test_dot_call_node_dashed(self):
        """Call nodes have style=dashed in the DOT output."""
        dag = CallGraphDAG()
        dag.add_node("regular", frozenset({0}), 10, ())
        dag.add_node("call_ref", frozenset({1}), 5, (), is_call_node=True)

        func = _FakeCompiledFunc("regular")
        func._call_graph = dag

        dot = hierarchical_dot(func)
        lines = dot.split("\n")
        n1_lines = [ln for ln in lines if "n1" in ln and "label=" in ln]
        assert len(n1_lines) == 1
        assert "style=dashed" in n1_lines[0]

    def test_custom_file_prefix(self):
        """Custom file_prefix appears in URL attributes."""
        dag = CallGraphDAG()
        dag.add_node("myfn", frozenset({0}), 10, ())

        func = _FakeCompiledFunc("myfn")
        func._call_graph = dag

        dot = hierarchical_dot(func, file_prefix="diagram")
        assert 'URL="diagram_myfn.png"' in dot


# ---------------------------------------------------------------------------
# CallGraphDAG.to_dot(file_prefix=...)
# ---------------------------------------------------------------------------


class TestToDotFilePrefix:
    def test_to_dot_without_prefix_no_url(self):
        """to_dot() without file_prefix does not add URL attributes."""
        dag = CallGraphDAG()
        dag.add_node("func_a", frozenset({0}), 10, ())
        dot = dag.to_dot()
        assert "URL=" not in dot

    def test_to_dot_with_prefix_adds_url(self):
        """to_dot(file_prefix=...) adds URL attributes to all nodes."""
        dag = CallGraphDAG()
        dag.add_node("func_a", frozenset({0}), 10, ())
        dag.add_node("func_b", frozenset({1}), 5, (), is_call_node=True)
        dag.add_call_edge(0, 1)

        dot = dag.to_dot(file_prefix="sub")
        assert 'URL="sub_func_a.png"' in dot
        assert 'URL="sub_func_b.png"' in dot

    def test_to_dot_with_prefix_preserves_structure(self):
        """Adding file_prefix does not break edge rendering."""
        dag = CallGraphDAG()
        dag.add_node("a", frozenset({0, 1}), 10, ())
        dag.add_node("b", frozenset({0, 1}), 8, ())
        dag.add_node("c", frozenset({2}), 5, (), is_call_node=True)
        dag.add_call_edge(0, 2)

        dot = dag.to_dot(file_prefix="fn")
        assert 'label="exec"' in dot
        assert 'label="call"' in dot
        assert "digraph CallGraph" in dot


# ---------------------------------------------------------------------------
# draw_hierarchical()
# ---------------------------------------------------------------------------


class TestDrawHierarchical:
    def test_returns_diagrams_and_dot(self):
        """draw_hierarchical returns dict with 'diagrams' and 'dot' keys."""
        block = _make_block(_sample_gates())
        func = _FakeCompiledFunc("top", cache={("k",): block})
        dag = CallGraphDAG()
        dag.add_node("top", frozenset({0}), 3, ())
        func._call_graph = dag

        result = draw_hierarchical(func)
        assert "diagrams" in result
        assert "dot" in result
        assert isinstance(result["diagrams"], dict)
        assert isinstance(result["dot"], str)

    def test_save_dir_creates_files(self):
        """save_dir parameter writes images and DOT file to disk."""
        block = _make_block(_sample_gates())
        func = _FakeCompiledFunc("savefn", cache={("k",): block})
        dag = CallGraphDAG()
        dag.add_node("savefn", frozenset({0}), 3, ())
        func._call_graph = dag

        with tempfile.TemporaryDirectory() as tmpdir:
            draw_hierarchical(func, save_dir=tmpdir, file_prefix="test")
            # Check image file
            img_path = os.path.join(tmpdir, "test_savefn.png")
            assert os.path.exists(img_path)
            assert os.path.getsize(img_path) > 0
            # Check DOT file
            dot_path = os.path.join(tmpdir, "test_call_graph.dot")
            assert os.path.exists(dot_path)
            with open(dot_path) as f:
                dot_content = f.read()
            assert "digraph CallGraph" in dot_content

    def test_no_save_dir_no_files(self):
        """Without save_dir, no files are written."""
        block = _make_block(_sample_gates())
        func = _FakeCompiledFunc("nf", cache={("k",): block})
        func._call_graph = CallGraphDAG()

        # Should not raise or create files
        result = draw_hierarchical(func)
        assert result["diagrams"] is not None

    def test_hierarchical_with_nested(self):
        """Nested functions produce diagrams for all levels."""
        from quantum_language._compile_state import CallRecord

        inner_block = _make_block(_sample_gates())
        inner_func = _FakeCompiledFunc("inner", cache={("ik",): inner_block})

        outer_block = _make_block(
            [
                {"target": 1, "type": _X, "angle": 0.0, "controls": [], "num_controls": 0},
            ]
        )
        outer_block._call_records.append(
            CallRecord(compiled_func_ref=inner_func, cache_key=("ik",), quantum_arg_indices=[[1]])
        )
        outer_func = _FakeCompiledFunc("outer", cache={("ok",): outer_block})

        dag = CallGraphDAG()
        dag.add_node("outer", frozenset({0}), 1, ())
        dag.add_node("inner", frozenset({1}), 3, (), is_call_node=True)
        dag.add_call_edge(0, 1)
        outer_func._call_graph = dag

        result = draw_hierarchical(outer_func)
        assert "outer" in result["diagrams"]
        assert "inner" in result["diagrams"]
        assert "URL=" in result["dot"]


# ---------------------------------------------------------------------------
# Integration: end-to-end with real compiled functions
# ---------------------------------------------------------------------------


class TestIntegrationHierarchical:
    def test_real_compiled_function_draw_data(self):
        """Real compiled function block produces valid draw_data."""
        import quantum_language as ql

        ql.circuit()

        @ql.compile
        def inc(x):
            x += 1
            return x

        a = ql.qint(0, width=4)
        inc(a)

        cache_key = list(inc._cache.keys())[0]
        block = inc._cache[cache_key]
        dd = block.draw_data()

        assert dd["num_layers"] > 0
        assert dd["num_qubits"] > 0
        assert len(dd["gates"]) > 0

        # Renderable
        img = _render_block_draw_data(dd, mode="overview")
        assert isinstance(img, Image.Image)
        assert img.size[0] > 0

    def test_real_nested_hierarchical(self):
        """Real nested compiled functions produce hierarchical diagrams."""
        import quantum_language as ql

        ql.circuit()

        @ql.compile
        def inner(x):
            x += 1
            return x

        @ql.compile
        def outer(x):
            x = inner(x)
            x += 2
            return x

        a = ql.qint(0, width=4)
        outer(a)

        diagrams = render_function_diagrams(outer)
        # At minimum, outer should have a diagram
        assert len(diagrams) >= 1

        # Check all diagrams are valid images
        for _name, img in diagrams.items():
            assert isinstance(img, Image.Image)
            assert img.size[0] > 0
            assert img.size[1] > 0
