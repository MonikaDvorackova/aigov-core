import pytest


def test_sigstore_dependency_importable() -> None:
    # We don't hit the network or require real bundles here.
    # This is a smoke test that the dependency is present and the API surface exists.
    import sigstore  # noqa: F401
    from sigstore.verify import Verifier  # noqa: F401


@pytest.mark.skip(reason="requires a real Sigstore bundle and identity")
def test_sigstore_verify_real_bundle() -> None:
    raise NotImplementedError

