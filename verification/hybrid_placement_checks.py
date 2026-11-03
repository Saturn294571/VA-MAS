"""Hybrid actor executes placements only after a Tev1 selection."""
from unittest.mock import patch
from langchain_core.tools import StructuredTool
from env.action_policy import guarded_tools, make_action_context

calls = []
def placeBlock(player_name: str, item_name: str, x: int, y: int, z: int,
               facing: str, emotion: list, murmur: str) -> dict:
    """Mock placement."""
    calls.append((x, y, z))
    return {"status": True}

tool = StructuredTool.from_function(placeBlock)
context = make_action_context("Alice", {"id": "1"}, {}, [tool], 5)
events = []
wrapped = guarded_tools(context, [tool], events, "hybrid")[0]
args = dict(player_name="Alice", item_name="stone", x=1, y=2, z=3, facing="A", emotion=[], murmur="")
with patch("model.ollama_decision.choose", return_value="defer"):
    assert not wrapped.run(args)["status"] and not calls
with patch("model.ollama_decision.choose", return_value="place"):
    assert wrapped.run(args)["status"] and len(calls) == 1
with patch("model.ollama_decision.choose", side_effect=TimeoutError()):
    assert not wrapped.run(args)["status"] and len(calls) == 1
assert [e["decision_choice"] for e in events] == ["defer", "place", "error"]
print("hybrid placement checks passed")
