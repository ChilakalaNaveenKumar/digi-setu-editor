"""Pydantic shapes for the workspace + session REST surface."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    """
    Request body for `POST /api/workspaces`.

    Web mode  : both fields optional. Server creates a fresh sandbox.
    Desktop mode: `path` is required (the absolute folder the user picked
                  via the OS dialog). `name` defaults to the folder basename.
    """

    name: Optional[str] = None
    path: Optional[str] = Field(default=None, description="Absolute path; required in desktop mode.")


class WorkspaceRename(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class WorkspaceRecord(BaseModel):
    id: str
    mode: Literal["web", "desktop"]
    path: str
    name: str
    owner_user_id: str
    created_at: str
    last_used: str


class SessionCreate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = Field(
        default=None,
        description=(
            "Optional model id to pin this session to "
            "(see GET /api/models). Falls back to the user's default."
        ),
    )


class SessionRename(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class SessionModelUpdate(BaseModel):
    """PATCH /api/sessions/{sid}/model — change the model in flight."""
    model: str = Field(min_length=1, max_length=120)


class SessionRecord(BaseModel):
    id: str
    workspace_id: str
    title: str
    model: Optional[str] = None
    created_at: str
    last_used: str
