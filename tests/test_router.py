from niuniu_agent.models import Challenge
from niuniu_agent.strategies.router import StrategyRouter


def test_router_prefers_keyword_override() -> None:
    challenge = Challenge(
        code="challenge-2",
        title="Company Portal",
        description="一个后台登录页面，web portal admin login",
        difficulty="easy",
        level=1,
    )

    strategy = StrategyRouter.default().route(challenge)

    assert strategy.track_id == "track2"


def test_router_falls_back_to_level_mapping() -> None:
    challenge = Challenge(
        code="challenge-4",
        title="Unknown Challenge",
        description="no matching keywords",
        difficulty="medium",
        level=4,
    )

    strategy = StrategyRouter.default().route(challenge)

    assert strategy.track_id == "track4"
