"""Router package — re-exports the APIRouters for the main app to mount."""

from src.routers import admin, agents, campaigns, candidates, people, webhooks

__all__ = ["admin", "agents", "campaigns", "candidates", "people", "webhooks"]
