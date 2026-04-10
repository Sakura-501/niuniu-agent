from niuniu_agent.strategies.base import TrackStrategy


STRATEGY = TrackStrategy(
    track_id="track3",
    name="track3-api-service",
    system_prompt=(
        "You are solving track 3. Focus on API behavior, JSON workflows, "
        "tokens, access control, schema discovery, and automation-friendly exploitation."
    ),
)
