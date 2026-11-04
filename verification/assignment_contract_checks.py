"""Offline behavior checks for Controller assignment contracts."""

import logging
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pipeline.assignment_policy import (
    from_legacy_proposal, graph_error, make_assignment_context, validate_assignment,
)
from type_define.graph import Graph, Task


class AssignmentContractChecks(unittest.TestCase):
    def setUp(self):
        self.first = Task("first", {})
        self.second = Task("second", {})
        for task in (self.first, self.second):
            task.candidate_list = ["Alice", "Bob"]
        self.graph = Graph()
        self.graph.add_node(self.first)
        self.graph.add_node(self.second)
        self.agents = [SimpleNamespace(name="Alice"), SimpleNamespace(name="Bob")]
        self.assignment = {}

    def context(self):
        return make_assignment_context([self.first, self.second], self.agents,
                                       self.assignment, self.graph)

    def decide(self, pairs):
        return {"kind": "assign", "source": "fixture", "assignments": [
            {"task_id": task.id, "agent_ids": agents} for task, agents in pairs]}

    def reason(self, decision, context=None, **kwargs):
        return validate_assignment(context or self.context(), decision, **kwargs)[1][0]["reason"]

    def test_valid_batch_and_reservations(self):
        accepted, rejected = validate_assignment(self.context(), self.decide([
            (self.first, ["Alice"]), (self.second, ["Bob"])]))
        self.assertEqual(len(accepted), 2)
        self.assertEqual(rejected, [])
        accepted, rejected = validate_assignment(self.context(), self.decide([
            (self.first, ["Alice"]), (self.second, ["Alice"])]))
        self.assertEqual(len(accepted), 1)
        self.assertEqual(rejected[0]["reason"], "agent_busy_or_reserved")
        self.assertEqual(self.reason(self.decide([(self.first, ["Alice"]),
                                                   (self.first, ["Bob"])])), "duplicate_task")

    def test_predecessors_cycles_and_unknown_edges(self):
        self.graph.add_edge(self.first, self.second)
        for status in (Task.unknown, Task.running, Task.failure):
            self.first.status = status
            self.assertEqual(self.reason(self.decide([(self.second, ["Bob"])])),
                             "predecessor_not_successful")
        self.first.status = Task.success
        self.assertFalse(validate_assignment(self.context(), self.decide([(self.second, ["Bob"])]))[1])
        self.graph.add_edge(self.second, self.first)
        self.assertEqual(graph_error(self.graph), "graph_cycle")
        self.assertEqual(self.reason(self.decide([(self.second, ["Bob"])])), "graph_cycle")
        self.graph.edge = [(self.first, Task("outside", {}))]
        self.assertEqual(graph_error(self.graph), "invalid_graph_edge")
        self.assertEqual(graph_error(None), "graph_unavailable")

    def test_legacy_indices_and_invalid_response(self):
        context = self.context()
        decision, rejected = from_legacy_proposal(context, [
            {"task_id": "1", "agent": "Alice"}, {"task_id": "99", "agent": "Bob"},
            {"task_id": True, "agent": "Alice"}, {"task_id": 0, "agent": None}])
        self.assertEqual(decision["assignments"][0]["task_id"], self.second.id)
        self.assertEqual([item["reason"] for item in rejected],
                         ["unknown_task", "invalid_task_index", "invalid_agents"])
        self.assertEqual(from_legacy_proposal(context, None)[1][0]["reason"], "invalid_response")

    def test_state_revalidation_and_constraints(self):
        decision = self.decide([(self.first, ["Alice"])])
        self.assertFalse(validate_assignment(self.context(), decision)[1])
        self.assignment["Alice"] = "other"
        self.assertEqual(self.reason(decision), "agent_busy_or_reserved")
        self.assignment.clear()
        self.first.candidate_list = ["Bob"]
        self.assertEqual(self.reason(decision), "ineligible_agent")
        self.first.candidate_list = ["Alice", "Bob"]
        self.first.number = 2
        self.assertEqual(self.reason(decision), "agent_count_or_duplicate")
        self.assertEqual(self.reason(self.decide([(self.first, ["Alice", "Bob"])]),
                                     allow_multi_agent=False), "unsupported_multi_agent")

    def test_existing_controllers_dispatch_only_validated_work(self):
        from pipeline.controller import GlobalController

        def make_controller(cls):
            ctrl = cls.__new__(cls)
            ctrl.task_manager = SimpleNamespace(graph=self.graph)
            ctrl.task_list = [self.first, self.second]
            ctrl.agent_list = self.agents
            ctrl.assignment = {}
            ctrl.logger = logging.getLogger("fixture")
            ctrl.task_list_lock = threading.Lock()
            ctrl.task_queue = []
            ctrl.collab_list = []
            ctrl.one_task_done = True
            return ctrl

        ctrl = make_controller(GlobalController)
        proposals = [{"task_id": "0", "agent": "Alice"}]
        valid = ctrl.validate_assignments(proposals)
        self.assertEqual(valid[0]["task_instance"], self.first)
        ctrl.assignment["Alice"] = "other"
        ctrl.execute_assignments(valid, assignment_mode="llm")
        self.assertEqual(ctrl.task_queue, [])
        ctrl.assignment.clear()
        with patch("pipeline.controller.time.sleep"):
            ctrl.execute_assignments(valid, assignment_mode="llm")
        self.assertEqual(ctrl.task_queue[0][0].name, "Alice")
        self.assertEqual(self.first.status, Task.running)



if __name__ == "__main__":
    unittest.main()
