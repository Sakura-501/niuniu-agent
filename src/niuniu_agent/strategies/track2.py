from niuniu_agent.strategies.base import TrackStrategy


STRATEGY = TrackStrategy(
    track_id="track2",
    name="track2-web-app",
    system_prompt=(
        "You are solving track 2. Focus on web app attack surface, routing, "
        "auth, parameters, file access, injection, and hidden admin functionality."
    ),
)
