class TriageResponse(BaseModel):
    is_emergency: bool
    tier: str
    esi_level: int
    severity: Optional[int] = None
        is_emergency=False,
        tier="TIER_2_HEURISTIC_CLINICAL_ENGINE",
        esi_level=esi,
        severity=payload.severity,
