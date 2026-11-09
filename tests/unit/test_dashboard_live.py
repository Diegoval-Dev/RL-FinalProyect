from dashboard.live import run_live_session
from wafarena.eval.harness import SessionPlan


class Env:
    def __init__(self):
        self.options = None
        self.steps = 0

    def reset(self, *, seed, options):
        self.options = (seed, options)
        return "observation", {
            "session_id": "s",
            "gt_label": "attack",
            "modsec_would_block": [False, True, True, True],
        }

    def step(self, action):
        self.steps += 1
        return (
            "next",
            0.0,
            self.steps == 2,
            False,
            {
                "session_id": "s",
                "gt_effect": self.steps == 1,
                "gt_label": "attack",
                "modsec_would_block": [False] * 4,
            },
        )


class Policy:
    def __init__(self):
        self.sessions = []

    def reset_session(self, session_id):
        self.sessions.append(session_id)

    def act(self, obs):
        return 1


def test_live_session_uses_pre_action_modsec_result_and_bounded_steps():
    env, policy = Env(), Policy()
    result = run_live_session(env, policy, SessionPlan(True, "base", 17), max_requests=1)
    assert env.options == (17, {"base_id": "base"})
    assert policy.sessions == ["s"]
    assert env.steps == 1
    assert result["complete"] is False
    assert result["events"] == [
        {
            "session_id": "s",
            "request_index": 1,
            "traffic": "attack",
            "defender_action": "BLOCK",
            "modsec_pl2": "BLOCK",
            "effect": True,
        }
    ]
