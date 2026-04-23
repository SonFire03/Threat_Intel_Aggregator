from pydantic import BaseModel


class WatchlistPatchRequest(BaseModel):
    watchlisted: bool
    reason: str | None = None
