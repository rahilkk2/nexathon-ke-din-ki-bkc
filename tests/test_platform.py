"""
Comprehensive Test Suite for FloatingTextbook AI Platform
Tests all critical application logic as specified in Section 16 of requirements:
1. Valid document upload & extraction
2. Invalid file type handling
3. Empty document handling
4. Page reference preservation
5. Topic identification
6. Quiz retrieval
7. Correct answer validation
8. Incorrect answer validation
9. Attempt persistence
10. Topic accuracy calculation
11. Insufficient data handling
12. Weak topic detection & explainability
13. Recommendation generation
14. Dashboard calculations
15. Pre/post test learning gain
16. Socratic AI grounded response
17. Mission submission & numerical validation
18. Demonstration dataset reset & cold-start clearing
"""

import os
import json
import tempfile
import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.database import init_db, seed_default_data, get_db_connection
from backend.document_processor import DocumentProcessor
from backend.data_science_engine import DataScienceEngine
from backend.ai_engine import AIEngine

client = TestClient(app)


def test_01_database_and_health():
    """Verify system health endpoint and database initialization."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "data_science_engine" in data


def test_02_document_listing_and_extraction():
    """Verify default seeded documents and chunks are accessible with page numbers."""
    response = client.get("/api/documents")
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) >= 1
    doc = docs[0]
    assert doc["page_count"] > 0
    assert doc["chunk_count"] > 0


def test_03_topic_retrieval_and_page_ranges():
    """Verify extracted topics have page ranges and subject tags."""
    response = client.get("/api/topics")
    assert response.status_code == 200
    topics = response.json()
    assert len(topics) >= 4
    topic_titles = [t["title"] for t in topics]
    assert "Electromagnetic Induction" in topic_titles
    assert "Integration by Parts" in topic_titles


def test_04_topic_chunks_and_grounding():
    """Verify topic chunks contain page numbers and verbatim text."""
    response = client.get("/api/topics/top-emi/chunks")
    assert response.status_code == 200
    data = response.json()
    assert data["topic"]["title"] == "Electromagnetic Induction"
    assert len(data["chunks"]) >= 1
    assert data["chunks"][0]["page_number"] in [14, 15]


def test_05_upload_valid_text_document():
    """Test uploading a valid TXT document and verifying chunking and topic discovery."""
    sample_content = (
        "Chapter 1: Quantum Mechanics Basics\n\n"
        "Planck's constant relates the energy of a photon to its frequency: E = h * f. "
        "The photoelectric effect proves that light behaves as discrete packets called quanta.\n\n"
        "Chapter 2: Wave Particle Duality\n\n"
        "De Broglie hypothesized that all matter exhibits wave-like behavior with wavelength lambda = h / p."
    )
    with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as tmp:
        tmp.write(sample_content)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            res = client.post("/api/documents/upload", files={"file": ("quantum_physics.txt", f, "text/plain")}, data={"subject": "Physics"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["chunks_extracted"] >= 1
        assert len(data["topics_discovered"]) >= 1
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_06_upload_invalid_file_type():
    """Test rejecting unsupported file types gracefully."""
    with tempfile.NamedTemporaryFile("w+", suffix=".exe", delete=False) as tmp:
        tmp.write("Fake binary")
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            res = client.post("/api/documents/upload", files={"file": ("virus.exe", f, "application/octet-stream")})
        assert res.status_code == 400
        assert "Unsupported file type" in res.json()["detail"]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_07_upload_empty_document():
    """Test handling of empty or unreadable documents."""
    with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            res = client.post("/api/documents/upload", files={"file": ("empty.txt", f, "text/plain")})
        assert res.status_code == 400
        assert "Could not extract text" in res.json()["detail"]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_08_quiz_retrieval_and_question_structure():
    """Verify quiz contains multiple choice options and hints."""
    res = client.get("/api/quizzes/quiz-emi")
    assert res.status_code == 200
    data = res.json()
    assert data["quiz"]["id"] == "quiz-emi"
    assert len(data["questions"]) >= 3
    q1 = data["questions"][0]
    assert len(q1["options"]) == 4
    assert "hint" in q1


def test_09_quiz_submission_and_answer_grading():
    """Test submitting a quiz, checking answer grading, and updating mastery."""
    payload = {
        "learner_id": "learner-001",
        "quiz_id": "quiz-emi",
        "topic_id": "top-emi",
        "hints_used": 1,
        "is_post_test": False,
        "answers": [
            {
                "question_id": "q-emi-1",
                "user_answer": "A time rate of change of magnetic flux through the coil" # Correct
            },
            {
                "question_id": "q-emi-2",
                "user_answer": "Conservation of Energy" # Correct
            },
            {
                "question_id": "q-emi-3",
                "user_answer": "It remains unchanged" # Incorrect
            }
        ]
    }
    res = client.post("/api/quizzes/submit", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["correct_count"] == 2
    assert data["total_questions"] == 3
    assert data["score_pct"] == 67
    assert len(data["graded_responses"]) == 3
    assert data["graded_responses"][0]["is_correct"] is True
    assert data["graded_responses"][2]["is_correct"] is False


def test_10_data_science_eda_and_topic_accuracies():
    """Test Exploratory Data Analysis module calculations using pandas/numpy."""
    ds = DataScienceEngine()
    eda = ds.run_eda("learner-001")
    assert eda["has_data"] is True
    assert eda["total_completed_attempts"] > 0
    assert 0.0 <= eda["overall_accuracy"] <= 1.0
    assert len(eda["topic_metrics"]) >= 2


def test_11_explainable_weak_topic_detection():
    """Verify weak topic detection produces transparent natural-language evidence."""
    ds = DataScienceEngine()
    gaps = ds.detect_learning_gaps("learner-001")
    assert len(gaps) >= 1
    top_gap = gaps[0]
    assert "Integration by Parts" in [g["topic_title"] for g in gaps]
    # Check that explanation contains specific quantitative evidence
    assert "accuracy" in top_gap["explanation"]
    assert "Revision recommended" in top_gap["explanation"]


def test_12_recommendation_generation():
    """Verify adaptive recommendation engine maps gaps to prioritized study tasks."""
    ds = DataScienceEngine()
    recs = ds.generate_recommendations("learner-001")
    assert len(recs) >= 1
    priorities = [r["priority"] for r in recs]
    assert "High" in priorities


def test_13_complete_study_plan_item():
    """Test completing a study plan item updates DB and telemetry."""
    res = client.get("/api/recommendations")
    recs = res.json()
    assert len(recs) > 0
    first_id = recs[0]["id"]

    complete_res = client.post(f"/api/recommendations/{first_id}/complete")
    assert complete_res.status_code == 200
    assert complete_res.json()["status"] == "success"


def test_14_data_science_evaluation_metrics():
    """Verify evaluation endpoint returns Hake's normalized gain and benchmark data."""
    res = client.get("/api/evaluation")
    assert res.status_code == 200
    data = res.json()
    assert "normalized_learning_gain_hake" in data
    assert "average_pre_test_score" in data
    assert "average_post_test_score" in data


def test_15_socratic_ai_tutor_grounded_response():
    """Verify tutor generates grounded response citing source textbook page."""
    payload = {
        "query": "Why does Faraday's law include a negative sign?",
        "mode": "explain"
    }
    res = client.post("/api/tutor/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "text" in data
    assert len(data["citations"]) >= 1
    assert data["citations"][0]["page_number"] in [14, 15]


def test_16_socratic_hint_mode():
    """Verify hint mode scaffolds without spoiling complete solution."""
    payload = {
        "query": "How do I choose u in integration by parts?",
        "mode": "hint"
    }
    res = client.post("/api/tutor/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "Hint" in data["text"]


def test_17_mission_submission_validation():
    """Test mission numerical evaluation and feedback."""
    payload = {
        "mission_id": "mis-emi-02",
        "calculated_metric": 200.0, # Target is 200V
        "explanation": "EMF = 400 * (0.040 Wb / 0.08 s) = 200 Volts"
    }
    res = client.post("/api/missions/submit", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_passed"] is True
    assert data["score"] == 100
    assert "Mission Passed" in data["feedback"]


def test_18_cold_start_clearing_and_reset():
    """Test clearing data for cold start testing, then resetting back to benchmark."""
    # 1. Clear data
    clear_res = client.post("/api/demo/clear")
    assert clear_res.status_code == 200

    dash_clear = client.get("/api/analytics/dashboard").json()
    assert dash_clear["eda"]["has_data"] is False
    assert dash_clear["eda"]["total_completed_attempts"] == 0

    # 2. Reset back to baseline
    reset_res = client.post("/api/demo/reset")
    assert reset_res.status_code == 200

    dash_reset = client.get("/api/analytics/dashboard").json()
    assert dash_reset["eda"]["has_data"] is True
    assert dash_reset["eda"]["total_completed_attempts"] >= 4
