# injector.py
from typing import List

def inject_values(steps: List[tuple], values: dict) -> List[tuple]:
    resolved = []

    for step in steps:
        if step[0] == "text" and step[1] in values:
            resolved.append(("text", values[step[1]]))
        else:
            resolved.append(step)

    return resolved