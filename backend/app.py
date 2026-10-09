"""
FloatingTextbook AI — FastAPI Backend Server
============================================
Full-stack REST API and static file server for:
- Textbook ingestion & chunk extraction
- Socratic AI companion & grounded citation retrieval
- Adaptive quiz engine & persistent assessment logging
- Data Science Engine (EDA, mastery estimation, gap detection, study planner)
- Interactive missions & learning labs
"""

import os
import shutil
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.database import init_db, seed_default_data, get_db_connection
from backend.document_processor import DocumentProcessor
from backend.data_science_engine import DataScienceEngine
from backend.ai_engine import AIEngine

# Initialize DB on startup
init_db()
seed_default_data()

app = FastAPI(
    title="FloatingTextbook AI API",
    description="Intelligent, Interactive, Data Science-Driven Adaptive Learning Platform",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

doc_processor = DocumentProcessor()
ds_engine = DataScienceEngine()
ai_engine = AIEngine()

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOADS_DIR = os.path.join(WORKSPACE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================
class ChatRequest(BaseModel):
    query: str
    mode: Optional[str] = "explain" # explain, hint, socratic_question, worked_example, test_me
    document_id: Optional[str] = None
    topic_id: Optional[str] = None

class QuestionAnswer(BaseModel):
    question_id: str
    user_answer: str

class QuizSubmitRequest(BaseModel):
    learner_id: Optional[str] = "learner-001"
    quiz_id: str
    topic_id: str
    answers: List[QuestionAnswer]
    hints_used: Optional[int] = 0
    is_post_test: Optional[bool] = False

class ApiKeyRequest(BaseModel):
    api_key: str

class MissionSubmitRequest(BaseModel):
    mission_id: str
    learner_id: Optional[str] = "learner-001"
    calculated_metric: float
    explanation: str


# =============================================================================
# 1. SYSTEM & HEALTH
# =============================================================================
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "FloatingTextbook AI",
        "version": "2.0.0",
        "data_science_engine": "active (pandas & numpy)",
        "ai_engine_mode": ai_engine.status_badge if hasattr(ai_engine, "status_badge") else "Grounded Engine Active",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# =============================================================================
# 2. DOCUMENT INGESTION & TEXTBOOKS
# =============================================================================
@app.get("/api/documents")
def list_documents():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT d.*, COUNT(c.id) as chunk_count
    FROM documents d
    LEFT JOIN document_chunks c ON d.id = c.document_id
    GROUP BY d.id
    ORDER BY d.uploaded_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...), subject: Optional[str] = Form("General STEM")):
    # Validate file type
    allowed_exts = [".pdf", ".txt", ".md", ".docx"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{file_ext}'. Please upload PDF, TXT, or MD.")

    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    saved_path = os.path.join(UPLOADS_DIR, f"{doc_id}_{file.filename}")

    # Write file to disk
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(saved_path)

    # Extract text page by page
    pages = doc_processor.extract_text_from_file(saved_path, file.filename)
    if not pages:
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from document. Scanned documents without text layer require OCR."
        )

    page_count = len(pages)
    title = os.path.splitext(file.filename)[0].replace("_", " ").title()
    summary = f"Textbook document containing {page_count} pages on {subject}."

    # Insert document
    conn = get_db_connection()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cur.execute("""
    INSERT INTO documents (id, filename, title, subject, file_size, page_count, uploaded_at, status, summary)
    VALUES (?, ?, ?, ?, ?, ?, ?, 'processed', ?)
    """, (doc_id, file.filename, title, subject, file_size, page_count, now, summary))
    conn.commit()
    conn.close()

    # Chunk and index
    chunks = doc_processor.chunk_and_index_document(doc_id, pages, default_topic=subject)
    # Extract topics
    extracted_topics = doc_processor.extract_topics_from_text(pages, doc_id, subject)

    # Log telemetry event
    ds_engine.log_event("learner-001", "document_uploaded", topic_id=None, metadata={
        "document_id": doc_id,
        "filename": file.filename,
        "pages": page_count,
        "chunks_indexed": len(chunks)
    })

    return {
        "status": "success",
        "document_id": doc_id,
        "title": title,
        "page_count": page_count,
        "chunks_extracted": len(chunks),
        "topics_discovered": extracted_topics
    }


# =============================================================================
# 3. TOPICS & TEXTBOOK EXPLORATION
# =============================================================================
@app.get("/api/topics")
def get_topics():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT t.*, d.title as doc_title,
           m.raw_accuracy, m.mastery_estimate, m.confidence_level, m.status as mastery_status
    FROM topics t
    LEFT JOIN documents d ON t.document_id = d.id
    LEFT JOIN topic_mastery m ON t.id = m.topic_id
    ORDER BY t.subject, t.title
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/topics/{topic_id}/chunks")
def get_topic_chunks(topic_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
    topic = cur.fetchone()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    cur.execute("""
    SELECT * FROM document_chunks
    WHERE topic = ? OR heading LIKE ?
    ORDER BY page_number ASC
    """, (topic["title"], f"%{topic['title']}%"))
    chunks = cur.fetchall()
    conn.close()

    # Log telemetry event
    ds_engine.log_event("learner-001", "topic_opened", topic_id=topic_id, metadata={
        "topic_title": topic["title"]
    })

    return {
        "topic": dict(topic),
        "chunks": [dict(c) for c in chunks]
    }


# =============================================================================
# 4. SOCRATIC AI COMPANION
# =============================================================================
@app.post("/api/tutor/chat")
def chat_with_tutor(req: ChatRequest):
    response = ai_engine.generate_socratic_response(
        query=req.query,
        mode=req.mode or "explain",
        document_id=req.document_id
    )

    # Log telemetry
    ds_engine.log_event("learner-001", "socratic_query", topic_id=req.topic_id, metadata={
        "mode": req.mode,
        "query_length": len(req.query)
    })

    return response


# =============================================================================
# 5. ADAPTIVE QUIZZES & ASSESSMENTS
# =============================================================================
@app.get("/api/quizzes")
def get_quizzes(topic_id: Optional[str] = Query(None)):
    conn = get_db_connection()
    cur = conn.cursor()
    sql = """
    SELECT q.*, t.title as topic_title, COUNT(qq.id) as question_count
    FROM quizzes q
    LEFT JOIN topics t ON q.topic_id = t.id
    LEFT JOIN quiz_questions qq ON q.id = qq.quiz_id
    """
    params = []
    if topic_id:
        sql += " WHERE q.topic_id = ?"
        params.append(topic_id)
    sql += " GROUP BY q.id ORDER BY q.created_at DESC"

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/quizzes/{quiz_id}")
def get_quiz_details(quiz_id: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT q.*, t.title as topic_title FROM quizzes q LEFT JOIN topics t ON q.topic_id = t.id WHERE q.id = ?", (quiz_id,))
    quiz = cur.fetchone()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    cur.execute("""
    SELECT id, quiz_id, topic_id, question_text, question_type, options_json, hint, difficulty, source_page
    FROM quiz_questions WHERE quiz_id = ?
    """, (quiz_id,))
    questions = cur.fetchall()
    conn.close()

    formatted_questions = []
    for q in questions:
        q_dict = dict(q)
        q_dict["options"] = json.loads(q_dict["options_json"]) if q_dict["options_json"] else []
        del q_dict["options_json"]
        formatted_questions.append(q_dict)

    # Log telemetry
    ds_engine.log_event("learner-001", "quiz_started", topic_id=quiz["topic_id"], metadata={"quiz_id": quiz_id})

    return {
        "quiz": dict(quiz),
        "questions": formatted_questions
    }

@app.post("/api/quizzes/submit")
def submit_quiz(req: QuizSubmitRequest):
    conn = get_db_connection()
    cur = conn.cursor()

    # Load questions with answer keys
    cur.execute("SELECT id, correct_answer, explanation, topic_id FROM quiz_questions WHERE quiz_id = ?", (req.quiz_id,))
    db_questions = {q["id"]: q for q in cur.fetchall()}

    if not db_questions:
        conn.close()
        raise HTTPException(status_code=404, detail="Quiz questions not found")

    correct_count = 0
    total_valid = len(req.answers)
    graded_responses = []
    now = datetime.now(timezone.utc).isoformat()
    attempt_id = f"att-{uuid.uuid4().hex[:8]}"

    for ans in req.answers:
        q_info = db_questions.get(ans.question_id)
        if not q_info:
            continue
        is_correct = 1 if ans.user_answer.strip().lower() == q_info["correct_answer"].strip().lower() else 0
        if is_correct:
            correct_count += 1

        graded_responses.append({
            "question_id": ans.question_id,
            "user_answer": ans.user_answer,
            "correct_answer": q_info["correct_answer"],
            "is_correct": bool(is_correct),
            "explanation": q_info["explanation"]
        })

    score = round(correct_count / max(1, total_valid), 3)

    # 1. Record parent assessment attempt first
    cur.execute("""
    INSERT INTO assessment_attempts (
        id, learner_id, quiz_id, topic_id, score, total_questions, correct_count,
        is_completed, is_post_test, started_at, completed_at, hints_used
    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
    """, (
        attempt_id, req.learner_id, req.quiz_id, req.topic_id, score, total_valid,
        correct_count, 1 if req.is_post_test else 0, now, now, req.hints_used
    ))

    # 2. Record child question responses
    for gr in graded_responses:
        resp_id = f"resp-{uuid.uuid4().hex[:8]}"
        cur.execute("""
        INSERT INTO question_responses (id, attempt_id, question_id, topic_id, user_answer, is_correct, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (resp_id, attempt_id, gr["question_id"], req.topic_id, gr["user_answer"], 1 if gr["is_correct"] else 0, now))

    conn.commit()
    conn.close()

    # Log telemetry event
    ds_engine.log_event(req.learner_id, "quiz_submitted", topic_id=req.topic_id, metadata={
        "attempt_id": attempt_id,
        "score": score,
        "correct_count": correct_count,
        "total": total_valid,
        "is_post_test": req.is_post_test
    })

    # Trigger automatic Data Science engine recalculation
    mastery_list = ds_engine.calculate_mastery(req.learner_id)
    gaps = ds_engine.detect_learning_gaps(req.learner_id, mastery_list=mastery_list)
    ds_engine.generate_recommendations(req.learner_id, gaps=gaps, mastery_list=mastery_list)

    # Find updated mastery for this topic
    updated_topic_mastery = next((m for m in mastery_list if m["topic_id"] == req.topic_id), None)

    return {
        "status": "success",
        "attempt_id": attempt_id,
        "score_pct": int(round(score * 100)),
        "correct_count": correct_count,
        "total_questions": total_valid,
        "graded_responses": graded_responses,
        "updated_mastery": updated_topic_mastery,
        "active_learning_gaps_count": len(gaps)
    }


# =============================================================================
# 6. DATA SCIENCE ANALYTICS & DASHBOARD
# =============================================================================
@app.get("/api/analytics/dashboard")
def get_analytics_dashboard(learner_id: Optional[str] = "learner-001"):
    eda = ds_engine.run_eda(learner_id)
    mastery = ds_engine.calculate_mastery(learner_id)
    gaps = ds_engine.detect_learning_gaps(learner_id)
    return {
        "eda": eda,
        "mastery_overview": mastery,
        "active_gaps": gaps
    }

@app.get("/api/mastery")
def get_mastery(learner_id: Optional[str] = "learner-001"):
    return ds_engine.calculate_mastery(learner_id)

@app.get("/api/gaps")
def get_learning_gaps(learner_id: Optional[str] = "learner-001"):
    return ds_engine.detect_learning_gaps(learner_id)

@app.get("/api/recommendations")
def get_recommendations(learner_id: Optional[str] = "learner-001"):
    return ds_engine.generate_recommendations(learner_id)

@app.post("/api/recommendations/{plan_id}/complete")
def complete_study_plan_item(plan_id: str, learner_id: Optional[str] = "learner-001"):
    conn = get_db_connection()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    cur.execute("""
    UPDATE study_plan_items
    SET is_completed = 1, completed_at = ?
    WHERE id = ? AND learner_id = ?
    """, (now, plan_id, learner_id))
    conn.commit()
    conn.close()

    ds_engine.log_event(learner_id, "revision_completed", metadata={"plan_id": plan_id})
    return {"status": "success", "completed_id": plan_id}

@app.get("/api/evaluation")
def get_evaluation(learner_id: Optional[str] = "learner-001"):
    return ds_engine.evaluate_model_performance(learner_id)


# =============================================================================
# 7. MISSION-BASED LEARNING
# =============================================================================
@app.get("/api/missions")
def get_missions():
    return [
        {
            "id": "mis-fin-01",
            "title": "Capital Growth & Debt Arbitrage Challenge",
            "subject": "Financial Mathematics",
            "topic": "Compound Interest",
            "scenario": (
                "You are an EdTech portfolio manager advising a STEM startup. "
                "The founders have a $10,000 research grant. Option A offers a guaranteed 7.5% annual return compounded monthly. "
                "Option B offers a high-yield term deposit at 8.0% compounded annually. Both have a 3-year term.\n\n"
                "Task: Calculate the final total payout for Option A (monthly compounding). "
                "Formula: A = P * (1 + r/n)^(n*t), where P=10000, r=0.075, n=12, t=3."
            ),
            "expected_target": 12514.46,
            "tolerance": 5.0, # Accept within +/- $5
            "learning_objective": "Model realistic discrete compounding intervals and quantify the impact of compounding frequency.",
            "rubric": "Accurate application of exponential growth equation and rounding."
        },
        {
            "id": "mis-emi-02",
            "title": "Clean Energy Hydro-Turbine Induction Sizing",
            "subject": "Physics",
            "topic": "Electromagnetic Induction",
            "scenario": (
                "A clean-energy hydro turbine has a generator rotor coil with N = 400 turns. "
                "During a rapid flow valve cycle lasting Delta t = 0.08 seconds, the magnetic flux through the coil changes "
                "from Phi_initial = 0.050 Wb to Phi_final = 0.010 Wb.\n\n"
                "Task: Calculate the magnitude of the induced electromotive force (EMF in Volts) across the coil terminals. "
                "Formula: |EMF| = N * |Delta Phi / Delta t|."
            ),
            "expected_target": 200.0,
            "tolerance": 2.0,
            "learning_objective": "Apply Faraday's Law to calculate generated voltage during rapid flux collapse.",
            "rubric": "Correct flux delta calculation and division by time delta."
        }
    ]

@app.post("/api/missions/submit")
def submit_mission(req: MissionSubmitRequest):
    # Lookup mission
    missions = get_missions()
    mission = next((m for m in missions if m["id"] == req.mission_id), None)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")

    target = mission["expected_target"]
    diff = abs(req.calculated_metric - target)
    is_passed = diff <= mission["tolerance"]

    feedback = ""
    score = 100 if is_passed else max(20, int(100 - (diff / target * 100)))

    if is_passed:
        feedback = (
            f"🎉 Mission Passed! Your calculated metric of {req.calculated_metric} is well within acceptable tolerance "
            f"(Target: {target}). Your explanation demonstrates clear understanding of {mission['topic']}!"
        )
    else:
        feedback = (
            f"⚠️ Needs Adjustment: Your submission of {req.calculated_metric} deviated from expected target {target}. "
            f"Check your exponential multiplication and period count (n * t). Review the textbook formula on page 38."
        )

    conn = get_db_connection()
    cur = conn.cursor()
    attempt_id = f"mis-att-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    cur.execute("""
    INSERT INTO mission_attempts (id, mission_id, learner_id, submitted_input, calculated_metric, is_passed, score, feedback, submitted_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (attempt_id, req.mission_id, req.learner_id, req.explanation, req.calculated_metric, 1 if is_passed else 0, score, feedback, now))
    conn.commit()
    conn.close()

    ds_engine.log_event(req.learner_id, "mission_completed", metadata={
        "mission_id": req.mission_id,
        "is_passed": is_passed,
        "score": score
    })

    return {
        "status": "success",
        "is_passed": is_passed,
        "score": score,
        "feedback": feedback
    }


# =============================================================================
# 8. SETTINGS & DEMO DATA MANAGEMENT
# =============================================================================
@app.post("/api/settings/apikey")
def update_api_key(req: ApiKeyRequest):
    ai_engine.set_api_key(req.api_key)
    return {
        "status": "success",
        "message": "Gemini API key updated",
        "has_live_gemini": ai_engine.has_live_gemini
    }

@app.post("/api/demo/reset")
def reset_demo_data():
    """Resets to baseline demonstration dataset or clears learner data."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM question_responses")
    cur.execute("DELETE FROM assessment_attempts")
    cur.execute("DELETE FROM learning_events")
    cur.execute("DELETE FROM topic_mastery")
    cur.execute("DELETE FROM study_plan_items")
    cur.execute("DELETE FROM mission_attempts")
    from backend.database import seed_baseline_attempts
    seed_baseline_attempts(cur)
    conn.commit()
    conn.close()

    # Recompute analytics
    ds_engine.calculate_mastery("learner-001")
    ds_engine.detect_learning_gaps("learner-001")
    ds_engine.generate_recommendations("learner-001")

    return {
        "status": "success",
        "message": "Reset to authentic baseline demonstration dataset."
    }

@app.post("/api/demo/clear")
def clear_all_learner_data():
    """Clears all records to test cold-start learner experience."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM question_responses")
    cur.execute("DELETE FROM assessment_attempts")
    cur.execute("DELETE FROM learning_events")
    cur.execute("DELETE FROM topic_mastery")
    cur.execute("DELETE FROM study_plan_items")
    cur.execute("DELETE FROM mission_attempts")
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "message": "All learner data cleared for empty-state verification."
    }


# =============================================================================
# STATIC ASSETS & ROOT ROUTING
# =============================================================================
app.mount("/static", StaticFiles(directory=WORKSPACE_DIR), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(WORKSPACE_DIR, "index.html"))

@app.get("/style.css")
def serve_css():
    return FileResponse(os.path.join(WORKSPACE_DIR, "style.css"))

@app.get("/script.js")
def serve_js():
    return FileResponse(os.path.join(WORKSPACE_DIR, "script.js"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)
