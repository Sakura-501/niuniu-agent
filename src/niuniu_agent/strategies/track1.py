from niuniu_agent.strategies.base import TrackStrategy


STRATEGY = TrackStrategy(
    track_id="track1",
    name="track1-linux-recon",
    system_prompt=(
        "You are solving track 1. Focus on Linux host exposure, services, "
        "weak auth, local privilege clues, filesystem artifacts, and command execution paths."
    ),
)
