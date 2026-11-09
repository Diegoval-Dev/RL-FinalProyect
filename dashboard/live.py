"""Bounded live lab session for the Streamlit demo."""

from wafarena.defenders.base import Action
from wafarena.eval.harness import SessionPlan


def run_live_session(env, policy, plan: SessionPlan, *, max_requests: int = 12) -> dict:
    """Run a single real-backend session and retain paired defender/PL2 decisions."""
    if not 1 <= max_requests <= 50:
        raise ValueError("max_requests must be between 1 and 50")
    options = {"base_id": plan.ref} if plan.is_attack else {"session_id": plan.ref}
    obs, info = env.reset(seed=plan.seed, options=options)
    policy.reset_session(info["session_id"])
    events = []
    complete = False
    for index in range(1, max_requests + 1):
        action = Action(policy.act(obs))
        current_info = info
        obs, _reward, terminated, truncated, info = env.step(int(action))
        events.append(
            {
                "session_id": current_info["session_id"],
                "request_index": index,
                "traffic": current_info["gt_label"],
                "defender_action": action.name,
                "modsec_pl2": "BLOCK" if current_info["modsec_would_block"][1] else "ALLOW",
                "effect": bool(info["gt_effect"]),
            }
        )
        if terminated or truncated:
            complete = True
            break
    return {"events": events, "complete": complete, "plan_seed": plan.seed, "plan_ref": plan.ref}
