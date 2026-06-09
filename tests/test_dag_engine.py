"""Comprehensive tests for DAG planning engine."""

import pytest

from helixops.domain.errors import CyclicDependencyError
from helixops.domain.models import TaskNode, Workflow
from helixops.planning.dag_engine import DAGPlanningEngine


class TestDAGPlanningEngine:
    """Tests for the DAG planning engine."""

    def test_linear_graph(self) -> None:
        """Test a simple linear dependency chain."""
        workflow = Workflow(name="Linear")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="c", name="C", depends_on=["b"]))

        engine = DAGPlanningEngine(workflow)
        plan = engine.plan()

        assert plan.max_depth == 2
        assert len(plan.waves) == 3
        assert plan.waves[0].task_ids == ["a"]
        assert plan.waves[1].task_ids == ["b"]
        assert plan.waves[2].task_ids == ["c"]

    def test_fan_out_graph(self) -> None:
        """Test a fan-out dependency pattern (one task to many)."""
        workflow = Workflow(name="FanOut")
        workflow.add_task(TaskNode(task_id="root", name="Root"))
        workflow.add_task(TaskNode(task_id="b1", name="B1", depends_on=["root"]))
        workflow.add_task(TaskNode(task_id="b2", name="B2", depends_on=["root"]))
        workflow.add_task(TaskNode(task_id="b3", name="B3", depends_on=["root"]))

        engine = DAGPlanningEngine(workflow)
        plan = engine.plan()

        assert len(plan.waves) == 2
        assert plan.waves[0].task_ids == ["root"]
        assert set(plan.waves[1].task_ids) == {"b1", "b2", "b3"}

    def test_fan_in_graph(self) -> None:
        """Test a fan-in dependency pattern (many tasks to one)."""
        workflow = Workflow(name="FanIn")
        workflow.add_task(TaskNode(task_id="a1", name="A1"))
        workflow.add_task(TaskNode(task_id="a2", name="A2"))
        workflow.add_task(TaskNode(task_id="a3", name="A3"))
        workflow.add_task(TaskNode(task_id="merge", name="Merge", depends_on=["a1", "a2", "a3"]))

        engine = DAGPlanningEngine(workflow)
        plan = engine.plan()

        assert len(plan.waves) == 2
        assert set(plan.waves[0].task_ids) == {"a1", "a2", "a3"}
        assert plan.waves[1].task_ids == ["merge"]

    def test_diamond_graph(self) -> None:
        """Test a diamond dependency pattern."""
        workflow = Workflow(name="Diamond")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="c", name="C", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="d", name="D", depends_on=["b", "c"]))

        engine = DAGPlanningEngine(workflow)
        plan = engine.plan()

        assert len(plan.waves) == 3
        assert plan.waves[0].task_ids == ["a"]
        assert set(plan.waves[1].task_ids) == {"b", "c"}
        assert plan.waves[2].task_ids == ["d"]

    def test_wide_graph(self) -> None:
        """Test a wide graph with many parallel tasks."""
        workflow = Workflow(name="Wide")
        workflow.add_task(TaskNode(task_id="root", name="Root"))

        # Add 10 parallel tasks
        for i in range(10):
            workflow.add_task(TaskNode(task_id=f"task{i}", name=f"Task{i}", depends_on=["root"]))

        engine = DAGPlanningEngine(workflow)
        plan = engine.plan()
        analysis = engine.analyze_graph()

        assert len(plan.waves) == 2
        assert len(plan.waves[1].task_ids) == 10
        assert analysis.max_width == 10

    def test_deep_graph(self) -> None:
        """Test a deep graph with many sequential layers."""
        workflow = Workflow(name="Deep")
        prev_id = None

        # Create 20 sequential tasks
        for i in range(20):
            task_id = f"task{i}"
            depends_on = [prev_id] if prev_id else []
            workflow.add_task(TaskNode(task_id=task_id, name=f"Task{i}", depends_on=depends_on))
            prev_id = task_id

        engine = DAGPlanningEngine(workflow)
        plan = engine.plan()

        assert len(plan.waves) == 20
        assert plan.max_depth == 19

    def test_cycle_detection_self_cycle(self) -> None:
        """Test detection of self-dependency cycles."""
        workflow = Workflow(name="SelfCycle")
        workflow.add_task(TaskNode(task_id="a", name="A", depends_on=["a"]))

        engine = DAGPlanningEngine(workflow)
        analysis = engine.analyze_graph()

        assert not analysis.is_acyclic
        assert len(analysis.has_cycles) > 0

    def test_cycle_detection_two_node_cycle(self) -> None:
        """Test detection of two-node cycles."""
        workflow = Workflow(name="TwoNodeCycle")
        workflow.add_task(TaskNode(task_id="a", name="A", depends_on=["b"]))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))

        engine = DAGPlanningEngine(workflow)

        with pytest.raises(CyclicDependencyError):
            engine.plan()

    def test_cycle_detection_three_node_cycle(self) -> None:
        """Test detection of three-node cycles."""
        workflow = Workflow(name="ThreeNodeCycle")
        workflow.add_task(TaskNode(task_id="a", name="A", depends_on=["c"]))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="c", name="C", depends_on=["b"]))

        engine = DAGPlanningEngine(workflow)

        with pytest.raises(CyclicDependencyError):
            engine.plan()

    def test_unreachable_tasks_detection(self) -> None:
        """Test detection of unreachable tasks."""
        workflow = Workflow(name="Unreachable")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="orphan", name="Orphan", depends_on=["nonexistent"]))

        engine = DAGPlanningEngine(workflow)

        # This should fail at workflow validation, not planning
        # But let's verify through analysis
        analysis = engine.analyze_graph()
        assert "orphan" in analysis.orphan_tasks

    def test_disconnected_components(self) -> None:
        """Test detection of disconnected graph components."""
        workflow = Workflow(name="Disconnected")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="x", name="X"))
        workflow.add_task(TaskNode(task_id="y", name="Y", depends_on=["x"]))

        engine = DAGPlanningEngine(workflow)
        analysis = engine.analyze_graph()

        assert not analysis.is_connected
        assert len(analysis.connected_components) == 2

    def test_topological_sort_determinism(self) -> None:
        """Test that topological sort is deterministic."""
        workflow = Workflow(name="Deterministic")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="c", name="C", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="d", name="D", depends_on=["b", "c"]))

        engine1 = DAGPlanningEngine(workflow)
        plan1 = engine1.plan()

        engine2 = DAGPlanningEngine(workflow)
        plan2 = engine2.plan()

        assert plan1.task_ordering == plan2.task_ordering

    def test_execution_wave_stability(self) -> None:
        """Test that execution waves are stable across multiple runs."""
        workflow = Workflow(name="StableWaves")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b1", name="B1", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="b2", name="B2", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="c", name="C", depends_on=["b1", "b2"]))

        plans = []
        for _ in range(3):
            engine = DAGPlanningEngine(workflow)
            plans.append(engine.plan())

        # All plans should be identical
        for i in range(1, len(plans)):
            assert len(plans[i].waves) == len(plans[0].waves)
            for j, wave in enumerate(plans[i].waves):
                assert set(wave.task_ids) == set(plans[0].waves[j].task_ids)

    def test_graph_depth_calculation(self) -> None:
        """Test correct calculation of graph depth."""
        workflow = Workflow(name="DepthTest")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="c", name="C", depends_on=["b"]))
        workflow.add_task(TaskNode(task_id="d", name="D", depends_on=["c"]))

        engine = DAGPlanningEngine(workflow)
        plan = engine.plan()

        assert plan.max_depth == 3

    def test_graph_width_calculation(self) -> None:
        """Test correct calculation of graph width."""
        workflow = Workflow(name="WidthTest")
        workflow.add_task(TaskNode(task_id="root", name="Root"))

        for i in range(5):
            workflow.add_task(TaskNode(task_id=f"t{i}", name=f"T{i}", depends_on=["root"]))

        engine = DAGPlanningEngine(workflow)
        analysis = engine.analyze_graph()

        assert analysis.max_width == 5

    def test_critical_path_detection(self) -> None:
        """Test detection of the critical path."""
        workflow = Workflow(name="CriticalPath")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="c", name="C", depends_on=["b"]))
        workflow.add_task(TaskNode(task_id="d", name="D", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="e", name="E", depends_on=["c", "d"]))

        engine = DAGPlanningEngine(workflow)
        analysis = engine.analyze_graph()

        assert len(analysis.critical_path) == 4  # a -> b -> c -> e
        assert analysis.critical_path[0] == "a"
        assert analysis.critical_path[-1] == "e"

    def test_parallelism_factor(self) -> None:
        """Test calculation of parallelism factor."""
        workflow = Workflow(name="Parallelism")
        workflow.add_task(TaskNode(task_id="root", name="Root"))

        for i in range(4):
            workflow.add_task(TaskNode(task_id=f"t{i}", name=f"T{i}", depends_on=["root"]))

        workflow.add_task(
            TaskNode(task_id="merge", name="Merge", depends_on=[f"t{i}" for i in range(4)])
        )

        engine = DAGPlanningEngine(workflow)
        plan = engine.plan()

        # 6 tasks / 3 waves = 2.0 average parallelism
        assert plan.parallelism_factor > 1.0

    def test_task_dependency_info_direct_deps(self) -> None:
        """Test that direct dependencies are correctly identified."""
        workflow = Workflow(name="DirectDeps")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="c", name="C", depends_on=["b"]))

        engine = DAGPlanningEngine(workflow)
        plan = engine.plan()

        assert plan.task_dependencies["a"].direct_dependencies == set()
        assert plan.task_dependencies["b"].direct_dependencies == {"a"}
        assert plan.task_dependencies["c"].direct_dependencies == {"b"}

    def test_task_dependency_info_transitive_deps(self) -> None:
        """Test that transitive dependencies are correctly identified."""
        workflow = Workflow(name="TransitiveDeps")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="c", name="C", depends_on=["b"]))

        engine = DAGPlanningEngine(workflow)
        plan = engine.plan()

        assert plan.task_dependencies["c"].transitive_dependencies == {"a", "b"}

    def test_empty_workflow(self) -> None:
        """Test planning an empty workflow."""
        workflow = Workflow(name="Empty")
        workflow.add_task(TaskNode(task_id="single", name="Single"))

        engine = DAGPlanningEngine(workflow)
        plan = engine.plan()

        assert len(plan.waves) == 1
        assert plan.waves[0].task_ids == ["single"]
        assert plan.max_depth == 0

    def test_complex_mixed_graph(self) -> None:
        """Test a complex graph with mixed patterns."""
        workflow = Workflow(name="Complex")

        # Root
        workflow.add_task(TaskNode(task_id="root", name="Root"))

        # Fan-out
        workflow.add_task(TaskNode(task_id="b1", name="B1", depends_on=["root"]))
        workflow.add_task(TaskNode(task_id="b2", name="B2", depends_on=["root"]))
        workflow.add_task(TaskNode(task_id="b3", name="B3", depends_on=["root"]))

        # Secondary layer
        workflow.add_task(TaskNode(task_id="c1", name="C1", depends_on=["b1"]))
        workflow.add_task(TaskNode(task_id="c2", name="C2", depends_on=["b2", "b3"]))

        # Fan-in to root
        workflow.add_task(TaskNode(task_id="final", name="Final", depends_on=["c1", "c2"]))

        engine = DAGPlanningEngine(workflow)
        plan = engine.plan()

        assert len(plan.task_ordering) == 7
        assert plan.max_depth == 3
        assert len(plan.waves) == 4

    def test_wave_prerequisites(self) -> None:
        """Test that wave prerequisites are correctly set."""
        workflow = Workflow(name="WavePrereqs")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="c", name="C", depends_on=["b"]))

        engine = DAGPlanningEngine(workflow)
        plan = engine.plan()

        assert len(plan.waves[0].prerequisites) == 0
        assert plan.waves[1].prerequisites == {0}
        assert plan.waves[2].prerequisites == {1}

    def test_get_wave_for_task(self) -> None:
        """Test retrieval of wave for a task."""
        workflow = Workflow(name="GetWave")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))

        engine = DAGPlanningEngine(workflow)
        plan = engine.plan()

        assert plan.get_wave_for_task("a") == 0
        assert plan.get_wave_for_task("b") == 1

    def test_get_predecessors(self) -> None:
        """Test retrieval of task predecessors."""
        workflow = Workflow(name="Predecessors")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="c", name="C", depends_on=["a", "b"]))

        engine = DAGPlanningEngine(workflow)
        plan = engine.plan()

        assert plan.get_predecessors("a") == set()
        assert plan.get_predecessors("b") == {"a"}
        assert plan.get_predecessors("c") == {"a", "b"}

    def test_get_successors(self) -> None:
        """Test retrieval of task successors."""
        workflow = Workflow(name="Successors")
        workflow.add_task(TaskNode(task_id="a", name="A"))
        workflow.add_task(TaskNode(task_id="b", name="B", depends_on=["a"]))
        workflow.add_task(TaskNode(task_id="c", name="C", depends_on=["a"]))

        engine = DAGPlanningEngine(workflow)
        plan = engine.plan()

        assert plan.get_successors("a") == {"b", "c"}
        assert plan.get_successors("b") == set()
