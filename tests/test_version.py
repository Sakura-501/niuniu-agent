from niuniu_agent import __version__


def test_version_is_exposed() -> None:
    assert __version__ == "0.1.11"
