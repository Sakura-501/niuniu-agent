from niuniu_agent.skills.tracks import TRACK_PROFILES, infer_track


def test_infer_track_for_domain_environment() -> None:
    assert infer_track("Active Directory domain with ldap and kerberos") == "track4"


def test_infer_track_for_cloud_ai_surface() -> None:
    assert infer_track("cloud metadata bucket and ai model service") == "track2"


def test_track_profiles_cover_all_tracks() -> None:
    assert set(TRACK_PROFILES.keys()) == {"track1", "track2", "track3", "track4"}
