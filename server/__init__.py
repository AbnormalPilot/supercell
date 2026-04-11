"""Server package — thin wrapper around the flat app module.

The project is structured flat (models.py, environment.py, etc. at the
repo root) for simplicity, but `openenv validate` requires a
`server/app.py` entry point with a `main()` function. This package
re-exports the root `app.main` so both layouts work.
"""
