"""Public read-only endpoint for engineering branches and regions."""

from fastapi import APIRouter

from app.etl.taxonomy import ENGINEERING_TAXONOMY, REGIONS

router = APIRouter(prefix="/api/taxonomy", tags=["taxonomy"])


@router.get("")
async def get_taxonomy() -> dict[str, object]:
    """Return the full branch/domain hierarchy and supported regions."""
    return {"branches": ENGINEERING_TAXONOMY, "regions": REGIONS}
