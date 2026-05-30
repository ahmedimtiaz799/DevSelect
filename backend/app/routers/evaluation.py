from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional, AsyncGenerator
from uuid import uuid4
import json
import urllib.parse
import logging
from langgraph.types import Command

from app.agents.agent3_lead_evaluator import GeminiQuotaExceededError
from app.dependencies import verify_token
from app.models.requests import ResumeRequest

logger = logging.getLogger("devselect")

router = APIRouter(prefix="/api/chat", tags=["evaluation"])


@router.post("/{chat_id}/upload")
async def upload_cv(
    chat_id: str,
    request: Request,
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
        "error": None,
    }

    graph = request.app.state.graph
    result = await graph.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": thread_id}},
    )

    if result.get("error"):
        logger.warning(f"Upload evaluation failed before interrupt : thread={thread_id} error={result['error']}")
        return JSONResponse(
            status_code=503,
            content={"error": result["error"]},
        )

    interrupts = result.get("__interrupt__") or []
    interrupt_payload = interrupts[0] if interrupts else None
    if hasattr(interrupt_payload, "value"):
        interrupt_payload = interrupt_payload.value

    if not isinstance(interrupt_payload, dict) or "scenario" not in interrupt_payload:
        logger.error(f"Upload evaluation returned no resume scenario : thread={thread_id}")
        return JSONResponse(
            status_code=500,
            content={"error": "Evaluation could not be started. Please try again."},
        )

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
        "github_url": str(body.selected_profile) if body.selected_profile else None,
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
        report_sent = False

        async for state_snapshot in result_stream:
            if state_snapshot.get("error"):
                error = state_snapshot["error"]
                logger.warning(f"SSE pipeline state error : thread={thread_id} error={error}")
                payload = {
                    "error": error,
                    "code": "EVALUATION_PIPELINE_ERROR",
                }
                yield f"event: error\ndata: {json.dumps(payload)}\n\n"
                return

            if not agent_2_status_sent and state_snapshot.get("github_analysis") is not None:
                yield f"event: status\ndata: {json.dumps({'text': 'Checking Github Repository...'})}\n\n"
                agent_2_status_sent = True
                logger.info(f"Agent 2 completed : thread={thread_id}")

            if not agent_3_status_sent and state_snapshot.get("report") is not None:
                yield f"event: status\ndata: {json.dumps({'text': 'Generating Recommendation...'})}\n\n"
                agent_3_status_sent = True
                logger.info(f"Agent 3 completed : thread={thread_id}")

                report: str = state_snapshot.get("report", "")
                if report:
                    report_sent = True
                for char in report:
                    yield f"event: token\ndata: {json.dumps({'text': char})}\n\n"

        if not report_sent:
            logger.warning(f"SSE stream ended without report : thread={thread_id}")
            payload = {
                "error": "Evaluation stopped unexpectedly. Please try again.",
                "code": "EVALUATION_STOPPED_UNEXPECTEDLY",
            }
            yield f"event: error\ndata: {json.dumps(payload)}\n\n"
            return

        yield f"event: done\ndata: {json.dumps({})}\n\n"
        logger.info(f"SSE stream completed : thread={thread_id}")

    except GeminiQuotaExceededError as e:
        logger.warning(f"SSE pipeline quota failure : thread={thread_id} error={e}", exc_info=True)
        payload = {
            "error": e.user_message,
            "code": e.code,
            "retry_after_seconds": e.retry_after_seconds,
        }
        yield f"event: error\ndata: {json.dumps(payload)}\n\n"
    except Exception as e:
        logger.exception(f"SSE pipeline failed : thread={thread_id} error={e}")
        yield f"event: error\ndata: {json.dumps({'error': 'Evaluation failed'})}\n\n"


@router.get("/{chat_id}/stream")
async def stream_evaluation(
    chat_id: str,
    request: Request,
    thread_id: str = Query(..., description="LangGraph thread id"),
    resume_payload_str: str = Query(
        ...,
        alias="resume_payload",
        description="URL encoded json from /upload or /resume response",
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

    graph = request.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}

    try:
        snapshot = await graph.aget_state(config)
    except Exception as e:
        logger.error(f"Failed to read checkpoint — thread={thread_id} error={e}")
        raise HTTPException(status_code=404, detail="No evaluation checkpoint found. Run /upload first.")

    if snapshot is None or not snapshot.values:
        raise HTTPException(status_code=404, detail="No evaluation checkpoint found. Run /upload first.")

    candidate_name = "Unknown Candidate"
    role = "Unknown Role"

    candidate = snapshot.values.get("candidate")
    if candidate:
        candidate_name = candidate.full_name or "Unknown Candidate"
        role = candidate.current_title or "Unknown Role"
    else:
        for task in (snapshot.tasks or []):
            for interrupt_obj in (getattr(task, "interrupts", None) or []):
                interrupt_val = getattr(interrupt_obj, "value", None)
                if isinstance(interrupt_val, dict):
                    name = interrupt_val.get("candidate_name")
                    if name:
                        candidate_name = name
                    break

    meta = {
        "candidate_name": candidate_name,
        "role": role,
    }

    return StreamingResponse(
        evaluation_stream_generator(thread_id, resume_payload, meta, graph),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
