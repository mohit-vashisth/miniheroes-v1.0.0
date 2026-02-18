from typing import List, Dict, Any

from ..core.logger import log

logger = log()


def inject_values(steps: List[tuple], values: Dict[str, Any]) -> List[tuple]:
    """
    Inject values into step placeholders.

    Args:
        steps: List of step tuples (action, value, ...)
        values: Dictionary mapping placeholder names to actual values

    Returns:
        New list of steps with placeholders replaced by actual values
    """
    logger.debug(f"[INJECT] Injecting values into {len(steps)} steps")
    logger.debug(f"[INJECT] Available placeholders: {list(values.keys())}")

    resolved = []
    replacements = 0

    for i, step in enumerate(steps, 1):
        if step[0] == "text" and len(step) > 1 and step[1] in values:
            placeholder = step[1]
            actual_value = values[placeholder]
            resolved.append(("text", actual_value))
            replacements += 1
            logger.debug(f"[INJECT] Step {i}: Replaced '{placeholder}' with '{actual_value}'")
        else:
            resolved.append(step)
            logger.debug(f"[INJECT] Step {i}: Kept original: {step}")

    if replacements > 0:
        logger.info(f"[INJECT] Replaced {replacements} placeholder(s) in steps")
    else:
        logger.debug("[INJECT] No placeholders replaced")

    return resolved


def inject_email_code(steps: List[tuple], email: str, code: str) -> List[tuple]:
    """
    Convenience function to inject both email and code placeholders.

    Args:
        steps: List of step tuples
        email: Actual email value
        code: Actual verification code value

    Returns:
        Steps with __EMAIL__ and __CODE__ replaced
    """
    logger.debug(f"[INJECT] Injecting email and code into steps")
    return inject_values(steps, {"__EMAIL__": email, "__CODE__": code})