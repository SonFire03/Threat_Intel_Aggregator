from pydantic import BaseModel


class IOCStatsResponse(BaseModel):
    total_iocs: int
    watchlisted_iocs: int
    average_priority_score: float
