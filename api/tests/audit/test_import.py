def test_audit_module_imports() -> None:
    """The audit module must be importable as a package."""
    from margin_api import audit  # noqa: F401
