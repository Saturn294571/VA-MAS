"""Offline checks for the optional repeated placement segment."""
from langchain_core.tools import StructuredTool
from env.action_policy import make_action_context
from env.repeated_placement import run_segment, targets


def placeBlock(player_name: str, item_name: str, x: int, y: int, z: int,
               facing: str, emotion: list, murmur: str) -> dict:
    """Place a block in a test double."""
    return {"status": x != 2, "message": "test feedback"}


tool = StructuredTool.from_function(placeBlock)
task = {"id": 1, "description": "line", "milestones": [
    "Smooth sandstone placed at [1, -60, 0]", "Smooth sandstone placed at [2, -60, 0]"]}
assert targets(task) == [("smooth_sandstone", 1, -60, 0), ("smooth_sandstone", 2, -60, 0)]
assert not targets({"milestones": ["do something", "then place"]})
assert targets({"milestones": ["Retrieve smooth_sandstone from inventory or nearby chests", "Place smooth_sandstone at [1, -60, 0], and [2, -60, 0]"]}) == targets(task)
assert targets({"description": "Retrieve from chest if necessary", "milestones": [
    "Obtain smooth sandstone from chest at [-4, -60, 0]",
    "Place smooth sandstone at [1, -60, 0]", "Place smooth sandstone at [2, -60, 0]"]}) == targets(task)
ctx = make_action_context("Alice", task, {"relevant_data": "facing: A"}, [tool], 7)
events = []
result = run_segment(ctx, [tool], events, lambda state, choices: "place")
assert result["reason"] == "placement_unconfirmed" and len(result["completed"]) == 1
assert len(events) == 2 and events[0]["policy"] == "tev1_repeated_placement"
ctx = make_action_context("Alice", task, {"relevant_data": "facing: A"}, [tool], 7)
events = []
result = run_segment(ctx, [tool], events, lambda state, choices: "handoff")
assert result["reason"] == "model_handoff" and not events
def fail(state, choices):
    raise TimeoutError()
assert run_segment(ctx, [tool], [], fail)["reason"] == "decision_error:TimeoutError"
print("repeated placement checks passed")
