from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, AsyncGenerator
from uuid import uuid4
import json
import urllib.parse
import logging
from langgraph.types import Command

from app.config import settings
from app.agents.graph import build_graph
from app.dependencies import verify_token

logger = logging.getLogger("devselect")

router = APIRouter(prefix="/api/chat", tags=["evaluation"])


class ResumeRequest(BaseModel):
    thread_id: str
    selected_profile: Optional[HttpUrl] = None


@router.post("/{chat_id}/upload")
async def upload_cv(
    chat_id: str,
    file: UploadFile = File(...),
    thread_id: Optional[str] = Form(None),
    user_id: str = Depends(verify_token),
):
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File should be less than 10Mb.")

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type.")

    magic = await file.read(4)
    if magic != b"%PDF":
        raise HTTPException(status_code=400, detail="Invalid file type.")

    await file.seek(0)

    original_name = file.filename or "upload.pdf"
    safe_name = "".join(
        c for c in original_name
        if c.isalnum() or c in ("-", "_", ".")
    )
    safe_name = safe_name[:100]
    if not safe_name:
        safe_name = "upload.pdf"

    pdf_bytes = await file.read()
    thread_id = thread_id or str(uuid4())

    initial_state = {
        "pdf_bytes": pdf_bytes,
        "thread_id": thread_id,
        "raw_cv_text": "",
        "candidate": None,
        "github_analysis": None,
        "report": None,
        "error": None
    }

    graph = await build_graph()
    result = await graph.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": thread_id}}
    )

    interrupt_payload = result.get("__interrupt__", [{}])[0]
    if hasattr(interrupt_payload, "value"):
        interrupt_payload = interrupt_payload.value

    scenario = interrupt_payload.get("scenario")

    if scenario == "MULTIPLE_FOUND":
        return JSONResponse(
            status_code=202,
            content={
                "thread_id": thread_id,
                "profiles": interrupt_payload.get("profiles", []),
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "thread_id": thread_id,
            "status": "ready_to_stream",
            "resume_payload": interrupt_payload,
        },
    )


@router.post("/{chat_id}/resume")
async def resume_evaluation(
    chat_id: str,
    body: ResumeRequest,
    user_id: str = Depends(verify_token),
):
    resume_payload = {
        "github_url": str(body.selected_profile),
        "scenario": "ACCESSIBLE",
    }

    return JSONResponse(
        status_code=200,
        content={
            "thread_id": body.thread_id,
            "status": "ready_to_stream",
            "resume_payload": resume_payload,
        },
    )


async def evaluation_stream_generator(
    thread_id: str,
    resume_payload: dict,
    meta: dict,
    graph,
) -> AsyncGenerator[str, None]:

    yield f"event: meta\ndata: {json.dumps(meta)}\n\n"
    logger.info(f"SSE stream started : thread={thread_id} meta={meta}")

    try:
        config = {"configurable": {"thread_id": thread_id}}

        result_stream = graph.astream(
            Command(resume=resume_payload),
            config=config,
            stream_mode="values",
        )

        agent_2_status_sent = False
        agent_3_status_sent = False

        async for state_snapshot in result_stream:

            if not agent_2_status_sent and state_snapshot.get("github_analysis") is not None:
                yield f"event: status\ndata: {json.dumps({'text': 'Checking Github Repository...'})}\n\n"
                agent_2_status_sent = True
                logger.info(f"Agent 2 completed : thread={thread_id}")

            if not agent_3_status_sent and state_snapshot.get("report") is not None:
                yield f"event: status\ndata: {json.dumps({'text': 'Generating Recommendation...'})}\n\n"
                agent_3_status_sent = True
                logger.info(f"Agent 3 completed : thread={thread_id}")

                report: str = state_snapshot.get("report", "")
                for char in report:
                    yield f"event: token\ndata: {json.dumps({'text': char})}\n\n"

        yield f"event: done\ndata: {json.dumps({})}\n\n"
        logger.info(f"SSE stream completed : thread={thread_id}")

    except Exception as e:
        logger.error(f"SSE pipeline failed : thread={thread_id} error={e}")
        yield f"event: error\ndata: {json.dumps({'error': 'Evaluation failed'})}\n\n"


@router.get("/{chat_id}/stream")
async def stream_evaluation(
    chat_id: str,
    thread_id: str = Query(..., description="LangGraph thread id"),
    resume_payload_str: str = Query(
        ...,
        alias="resume_payload",
        description="URL encoded json from /upload or /resume response"
    ),
    user_id: str = Depends(verify_token),
):
    try:
        resume_payload = json.loads(urllib.parse.unquote(resume_payload_str))
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=422,
            detail=f"resume_payload must be valid URL-encoded JSON: {e}",
        )

    if "scenario" not in resume_payload:
        raise HTTPException(
            status_code=422,
            detail="resume_payload must contain a 'scenario' field.",
        )

    graph = await build_graph()
    config = {"configurable": {"thread_id": thread_id}}

    try:
        snapshot = await graph.aget_state(config)
    except Exception as e:
        logger.error(f"Failed to read checkpoint — thread={thread_id} error={e}")
        raise HTTPException(status_code=404, detail="No evaluation checkpoint found. Run /upload first.")

    if snapshot is None or not snapshot.values:
        raise HTTPException(status_code=404, detail="No evaluation checkpoint found. Run /upload first.")

    state = snapshot.values
    candidate = state.get("candidate")
    meta = {
        "candidate_name": candidate.full_name if candidate else "Unknown Candidate",
        "role": candidate.role if candidate else "Unknown Role",
    }

    return StreamingResponse(
        evaluation_stream_generator(thread_id, resume_payload, meta, graph),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )



    

    
