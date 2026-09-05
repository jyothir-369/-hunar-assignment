"""Router package — re-exports the APIRouters for the main app to mount."""

from src.routers import agents, campaigns, candidates, people, webhooks

__all__ = ["agents", "campaigns", "candidates", "people", "webhooks"]
