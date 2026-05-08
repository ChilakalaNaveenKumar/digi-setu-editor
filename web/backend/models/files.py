"""Request/response shapes for the workspace-files endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class FileWrite(BaseModel):
    """`POST /api/workspaces/{wsid}/fs/file`."""

    path: str = Field(min_length=1)
    content: str = ""
    overwrite: bool = False


class FolderCreate(BaseModel):
    """`POST /api/workspaces/{wsid}/fs/folder`."""

    path: str = Field(min_length=1)


class PathRename(BaseModel):
    """`POST /api/workspaces/{wsid}/fs/rename`."""

    from_: str = Field(alias="from", min_length=1)
    to: str = Field(min_length=1)

    model_config = {"populate_by_name": True}


class PathCopy(BaseModel):
    """`POST /api/workspaces/{wsid}/fs/copy` — `to` optional (Finder-style duplicate)."""

    from_: str = Field(alias="from", min_length=1)
    to: Optional[str] = None

    model_config = {"populate_by_name": True}


class PathMove(BaseModel):
    """`POST /api/workspaces/{wsid}/fs/move`."""

    from_: str = Field(alias="from", min_length=1)
    to: str = Field(min_length=1)

    model_config = {"populate_by_name": True}


class TerminalCreate(BaseModel):
    """`POST /api/terminals`."""

    shell: Optional[str] = None
    cwd: Optional[str] = None
    cols: Optional[int] = Field(default=80, ge=1, le=1000)
    rows: Optional[int] = Field(default=24, ge=1, le=1000)
