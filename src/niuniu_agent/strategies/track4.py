from niuniu_agent.strategies.base import TrackStrategy


STRATEGY = TrackStrategy(
    track_id="track4",
    name="track4-misc-depth",
    system_prompt=(
        "You are solving track 4. Focus on atypical workflows, chained exploits, "
        "binary or file artifacts, hidden transformations, and deep inspection."
    ),
)
