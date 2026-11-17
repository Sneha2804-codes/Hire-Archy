"""Candidate CV upload and extraction endpoint."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.matcher import embed_cv, extract_candidate_profile, extract_pdf_text
from app.db import get_db
from app.models import CandidateProfile

router = APIRouter(prefix="/api/cv", tags=["cv"])
MAX_CV_BYTES = 12 * 1024 * 1024


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Extract a PDF CV, embed its text, and persist a candidate profile."""
    filename = file.filename or "candidate.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Please upload a PDF file")
    pdf_bytes = await file.read(MAX_CV_BYTES + 1)
    if len(pdf_bytes) > MAX_CV_BYTES:
        raise HTTPException(status_code=413, detail="PDF must be 12 MB or smaller")
    try:
        raw_text = extract_pdf_text(pdf_bytes)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    extracted = await extract_candidate_profile(raw_text)
    embedding = await embed_cv(raw_text)
    profile = CandidateProfile(
        filename=filename[:255],
        raw_text=raw_text,
        extracted_data=extracted,
        embedding=embedding,
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return {"id": profile.id, "filename": profile.filename, **extracted}
