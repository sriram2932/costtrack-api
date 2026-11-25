"""In-memory store for the CostTrack API.

Demo only: everything lives in memory and resets when the server restarts.
One seeded project (see seed.py) and the draft estimates created through
the API. Tests reset the drafts between runs.
"""

from .seed import CURRENCY, ITEMS, PROJECT_ID

PROJECTS = {
    PROJECT_ID: {
        "project_id": PROJECT_ID,
        "currency": CURRENCY,
        "items": list(ITEMS),
    }
}

# project_id -> latest draft estimate dict (or nothing when no draft exists)
DRAFTS = {}


def get_project(project_id):
    return PROJECTS.get(project_id)


def get_draft(project_id):
    return DRAFTS.get(project_id)


def save_draft(project_id, draft):
    DRAFTS[project_id] = draft


def reset():
    """Clear drafts. Used by the test suite."""
    DRAFTS.clear()
