from __future__ import annotations
import json
from fastapi import APIRouter, HTTPException, Query, Request

from arenaflow.api.schemas import FanAsk, FanAnswer, OpsAsk, OpsAnswer
from arenaflow.config import Settings
from arenaflow.core.llm import detect_language, fan_reply, ops_reply
from arenaflow.core.retriever import Retriever
from arenaflow.data.kb import venue_cities
from arenaflow.data.ops import snapshot, venue_names

router = APIRouter()


def _retriever(request: Request) -> Retriever:
    r = getattr(request.app.state, "retriever", None)
    if r is None:
        r = Retriever()
        request.app.state.retriever = r
    return r


def _settings(request: Request) -> Settings:
    return request.app.state.settings


@router.get("/api/health")
async def health() -> dict:
    return {"ok": True, "service": "arenaflow"}


@router.get("/api/venues")
async def venues() -> dict:
    return {"venues": venue_names()}

@router.get("/api/cities")
async def cities() -> dict:
    return {"cities": [{"label": t, "city": c} for t, c in venue_cities()]}


@router.post("/api/fan/ask", response_model=FanAnswer)
async def fan_ask(body: FanAsk, request: Request) -> FanAnswer:
    settings = _settings(request)
    retriever = _retriever(request)
    snippets = retriever.search(body.query, top_k=3, city=body.city)
    lang = detect_language(body.query)
    reply = await fan_reply(body.query, snippets, settings.nvidia_api_key, settings.nvidia_model)
    return FanAnswer(
        text=reply.text,
        language=lang,
        source=reply.source,
        model=reply.model,
        used_ids=reply.used_ids,
    )


@router.post("/api/ops/ask", response_model=OpsAnswer)
async def ops_ask(body: OpsAsk, request: Request) -> OpsAnswer:
    settings = _settings(request)
    retriever = _retriever(request)
    try:
        snap = snapshot(body.venue, body.minute)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    snippets = retriever.search(body.question, top_k=2, city=snap.city)
    snap_dict = snap.to_dict()
    reply = await ops_reply(
        body.question,
        snippets,
        json.dumps(snap_dict),
        settings.nvidia_api_key,
        settings.nvidia_model,
    )
    return OpsAnswer(
        text=reply.text,
        source=reply.source,
        model=reply.model,
        used_ids=reply.used_ids,
        snapshot=snap_dict,
    )


@router.get("/api/ops/snapshot")
async def ops_snapshot(venue: str, minute: int = Query(60, ge=0, le=240)) -> dict:
    try:
        return snapshot(venue, minute).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
