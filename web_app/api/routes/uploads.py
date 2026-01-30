# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""File upload endpoint."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ...core.config import AppConfig
from ...models.task import UploadResponse
from ..dependencies import get_config

router = APIRouter(prefix="/api/upload", tags=["uploads"])

FILE_TYPE_MAP = {
    ".xlsx": "Excel",
    ".xls": "Excel",
    ".csv": "CSV",
    ".pdf": "PDF",
    ".doc": "Word",
    ".docx": "Word",
    ".txt": "Text",
    ".json": "JSON",
    ".png": "Image",
    ".jpg": "Image",
    ".jpeg": "Image",
    ".mp3": "Audio",
    ".wav": "Audio",
    ".mp4": "Video",
}


@router.post("", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    config: AppConfig = Depends(get_config),
) -> UploadResponse:
    """Upload a file for task processing."""
    # Validate extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in config.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {ext} not allowed. Allowed: {', '.join(sorted(config.allowed_extensions))}",
        )

    # Create upload directory
    file_id = uuid.uuid4().hex
    upload_dir = config.uploads_dir / file_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = upload_dir / (file.filename or "uploaded_file")
    content = await file.read()

    # Check file size
    if len(content) > config.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {config.max_upload_size_mb}MB",
        )

    with open(file_path, "wb") as f:
        f.write(content)

    return UploadResponse(
        file_id=file_id,
        file_name=file.filename or "uploaded_file",
        file_type=FILE_TYPE_MAP.get(ext, "File"),
        absolute_file_path=str(file_path.absolute()),
    )
