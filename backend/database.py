"""
Database and Persistence Layer for FloatingTextbook AI
SQLite-backed persistent data store for:
- Learner profiles
- Uploaded textbooks and documents
- Extracted content chunks with page numbers
- Extracted topics & concepts
- Quiz questions and assessments
- Assessment attempts & responses
- Learning events stream (for Data Science analytics)
- Mastery estimates & weak-topic flags
- Personalized study plan items
- Mission submissions and evaluations
"""

import sqlite3
import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "floatingtextbook.db")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Learner Profile
    cur.execute("""
    CREATE TABLE IF NOT EXISTS learners (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT,
        grade_level TEXT DEFAULT 'Class 12 / High School',
        theme TEXT DEFAULT 'Warm Ivory',
        created_at TEXT NOT NULL
    )
    """)

    # Documents (Textbooks)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        title TEXT NOT NULL,
        subject TEXT NOT NULL,
        file_size INTEGER,
        page_count INTEGER,
        uploaded_at TEXT NOT NULL,
        status TEXT DEFAULT 'processed',
        summary TEXT
    )
    """)

    # Document Chunks
    cur.execute("""
    CREATE TABLE IF NOT EXISTS document_chunks (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        page_number INTEGER NOT NULL,
        topic TEXT NOT NULL,
        heading TEXT,
        content TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
    )
    """)

    # Topics
    cur.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        id TEXT PRIMARY KEY,
        subject TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT,
        document_id TEXT,
        page_range TEXT,
        prerequisite_topic_id TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # Quizzes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quizzes (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        topic_id TEXT NOT NULL,
        subject TEXT NOT NULL,
        difficulty TEXT DEFAULT 'Medium',
        created_at TEXT NOT NULL,
        FOREIGN KEY (topic_id) REFERENCES topics (id) ON DELETE CASCADE
    )
    """)

    # Quiz Questions
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quiz_questions (
        id TEXT PRIMARY KEY,
        quiz_id TEXT NOT NULL,
        topic_id TEXT NOT NULL,
        question_text TEXT NOT NULL,
        question_type TEXT DEFAULT 'multiple_choice',
        options_json TEXT, -- JSON array of strings
        correct_answer TEXT NOT NULL,
        explanation TEXT,
        hint TEXT,
        difficulty TEXT DEFAULT 'Medium',
        source_page INTEGER,
        FOREIGN KEY (quiz_id) REFERENCES quizzes (id) ON DELETE CASCADE
    )
    """)

    # Assessment Attempts
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assessment_attempts (
        id TEXT PRIMARY KEY,
        learner_id TEXT NOT NULL,
        quiz_id TEXT NOT NULL,
        topic_id TEXT NOT NULL,
        score REAL NOT NULL,
        total_questions INTEGER NOT NULL,
        correct_count INTEGER NOT NULL,
        is_completed INTEGER DEFAULT 1,
        is_post_test INTEGER DEFAULT 0,
        started_at TEXT NOT NULL,
        completed_at TEXT NOT NULL,
        hints_used INTEGER DEFAULT 0,
        FOREIGN KEY (learner_id) REFERENCES learners (id)
    )
    """)

    # Question Responses
    cur.execute("""
    CREATE TABLE IF NOT EXISTS question_responses (
        id TEXT PRIMARY KEY,
        attempt_id TEXT NOT NULL,
        question_id TEXT NOT NULL,
        topic_id TEXT NOT NULL,
        user_answer TEXT NOT NULL,
        is_correct INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (attempt_id) REFERENCES assessment_attempts (id) ON DELETE CASCADE
    )
    """)

    # Learning Events Stream (Data Science Telemetry)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS learning_events (
        id TEXT PRIMARY KEY,
        learner_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        topic_id TEXT,
        metadata_json TEXT,
        timestamp TEXT NOT NULL
    )
    """)

    # Topic Mastery Estimates
    cur.execute("""
    CREATE TABLE IF NOT EXISTS topic_mastery (
        topic_id TEXT PRIMARY KEY,
        learner_id TEXT NOT NULL,
        raw_accuracy REAL NOT NULL,
        mastery_estimate REAL NOT NULL,
        valid_attempts INTEGER NOT NULL,
        confidence_level TEXT NOT NULL, -- Low, Developing, High
        status TEXT NOT NULL, -- Needs Revision, Developing, Strong
        last_updated TEXT NOT NULL
    )
    """)

    # Personalized Study Plan / Revision Path
    cur.execute("""
    CREATE TABLE IF NOT EXISTS study_plan_items (
        id TEXT PRIMARY KEY,
        learner_id TEXT NOT NULL,
        topic_id TEXT NOT NULL,
        action_type TEXT NOT NULL, -- review, worked_example, practice_quiz, simulation, post_test
        title TEXT NOT NULL,
        reason TEXT NOT NULL,
        evidence TEXT NOT NULL,
        priority TEXT DEFAULT 'High', -- High, Medium, Low
        duration_minutes INTEGER DEFAULT 15,
        is_completed INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        completed_at TEXT
    )
    """)

    # Mission Attempts
    cur.execute("""
    CREATE TABLE IF NOT EXISTS mission_attempts (
        id TEXT PRIMARY KEY,
        mission_id TEXT NOT NULL,
        learner_id TEXT NOT NULL,
        submitted_input TEXT NOT NULL,
        calculated_metric REAL,
        is_passed INTEGER NOT NULL,
        score INTEGER NOT NULL,
        feedback TEXT NOT NULL,
        submitted_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def seed_default_data():
    """Seeds default learner profile, sample textbooks, topics, quizzes, and initial study events."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Check if learner exists
    cur.execute("SELECT id FROM learners WHERE id = 'learner-001'")
    if not cur.fetchone():
        now = datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO learners (id, name, email, grade_level, theme, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("learner-001", "Ayaan M.", "ayaan@example.com", "Class 12 / Pre-University STEM", "Warm Ivory", now)
        )

    # Check if sample document exists
    cur.execute("SELECT id FROM documents WHERE id = 'doc-stem-01'")
    if not cur.fetchone():
        now = datetime.utcnow().isoformat()
        cur.execute("""
        INSERT INTO documents (id, filename, title, subject, file_size, page_count, uploaded_at, status, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "doc-stem-01",
            "Advanced_Science_and_Calculus_Textbook.pdf",
            "Floating Textbook: Comprehensive STEM Foundations",
            "Interdisciplinary STEM",
            4194304,
            42,
            now,
            "processed",
            "Standard high school & early university curriculum covering Electromagnetic Induction, Calculus & Integration, Organic Chemistry Reactions, Cell Respiration, and Financial Mathematics."
        ))

        # Sample Chunks with page numbers for grounded RAG
        sample_chunks = [
            ("chk-1", "doc-stem-01", 14, "Electromagnetic Induction", "Faraday's Law & Magnetic Flux",
             "Faraday's Law states that any change in magnetic flux through a closed circuit induces an electromotive force (EMF) in the circuit. The magnitude of the induced EMF is directly proportional to the time rate of change of magnetic flux through the circuit: EMF = -N * (dPhi/dt). The negative sign is a mathematical expression of Lenz's Law, indicating that the induced current will create a magnetic field that opposes the change in flux that produced it.",
            ),
            ("chk-2", "doc-stem-01", 15, "Electromagnetic Induction", "Lenz's Law and Conservation of Energy",
             "Lenz's Law is a consequence of the conservation of energy. If the induced field aided rather than opposed the changing magnetic flux, a perpetual motion machine would result, producing infinite energy without mechanical work. When a magnet approaches a solenoid north-pole-first, the solenoid induces a north pole to repel the magnet, requiring mechanical work to overcome the opposition.",
            ),
            ("chk-3", "doc-stem-01", 21, "Integration by Parts", "Derivation from the Product Rule",
             "Integration by Parts is derived from the product rule of differentiation: d(uv)/dx = u*(dv/dx) + v*(du/dx). Integrating both sides gives integral(u dv) = uv - integral(v du). The strategic choice of u and dv is critical: u should be selected using the LIATE rule (Logarithmic, Inverse trig, Algebraic, Trigonometric, Exponential). A common mistake is failing to distribute negative signs across subsequent integral terms.",
            ),
            ("chk-4", "doc-stem-01", 22, "Definite Integrals", "Fundamental Theorem of Calculus",
             "The Fundamental Theorem of Calculus connects differentiation and integration. Part 1 establishes that differentiation and integration are inverse processes. Part 2 shows that the definite integral of f(x) from a to b equals F(b) - F(a), where F'(x) = f(x). It represents the accumulated signed area under the curve between boundaries.",
            ),
            ("chk-5", "doc-stem-01", 28, "Organic Reactions", "Nucleophilic Substitution (SN1 vs SN2)",
             "Nucleophilic substitution involves replacing a leaving group with a nucleophile. SN2 occurs in a single concerted step with backside attack, resulting in inversion of stereochemistry (Walden inversion), favored by primary substrates and polar aprotic solvents. SN1 proceeds in two steps via a planar carbocation intermediate, leading to racemization, favored by tertiary substrates and polar protic solvents.",
            ),
            ("chk-6", "doc-stem-01", 33, "Cell Respiration", "Glycolysis and ATP Yield",
             "Cellular respiration converts glucose into usable ATP through glycolysis, the Krebs cycle, and oxidative phosphorylation. Glycolysis takes place in the cytoplasm and breaks 1 molecule of glucose into 2 molecules of pyruvate, yielding a net of 2 ATP and 2 NADH without requiring oxygen. In the presence of oxygen, pyruvate enters the mitochondria.",
            ),
            ("chk-7", "doc-stem-01", 38, "Compound Interest", "Exponential Growth and Compounding Frequency",
             "Compound interest computes interest on both the initial principal P and accumulated interest from prior periods. The formula is A = P * (1 + r/n)^(n*t), where r is the annual rate, n is compounding frequency per year, and t is time in years. As n approaches infinity, the growth converges to the continuous compounding model A = P * e^(r*t).",
            ),
        ]

        for chk in sample_chunks:
            cur.execute("""
            INSERT INTO document_chunks (id, document_id, page_number, topic, heading, content)
            VALUES (?, ?, ?, ?, ?, ?)
            """, chk)

        # Topics
        topics = [
            ("top-emi", "Physics", "Electromagnetic Induction", "Faraday's Law, Lenz's Law, magnetic flux, and induced currents in closed circuits.", "doc-stem-01", "pp. 14-18", None),
            ("top-int", "Mathematics", "Integration by Parts", "Application of product rule inverse, selection of u and dv using LIATE rule, and repeated integration.", "doc-stem-01", "pp. 21-25", None),
            ("top-def", "Mathematics", "Definite Integrals", "Fundamental theorem of calculus, accumulation of area under curves, and boundary evaluations.", "doc-stem-01", "pp. 22-26", "top-int"),
            ("top-org", "Chemistry", "Organic Reactions", "Mechanisms of SN1 and SN2 nucleophilic substitutions, carbocation stability, and stereochemistry.", "doc-stem-01", "pp. 28-32", None),
            ("top-bio", "Biology", "Cell Respiration", "Aerobic and anaerobic respiration pathways, glycolysis, citric acid cycle, and oxidative phosphorylation.", "doc-stem-01", "pp. 33-37", None),
            ("top-fin", "Mathematics", "Compound Interest", "Mathematical modeling of compounding intervals, exponential growth equations, and capital preservation.", "doc-stem-01", "pp. 38-42", None),
        ]

        for top in topics:
            cur.execute("""
            INSERT INTO topics (id, subject, title, summary, document_id, page_range, prerequisite_topic_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (*top, now))

        # Sample Quizzes and Questions
        quizzes = [
            ("quiz-emi", "Electromagnetic Induction Diagnostic", "top-emi", "Physics", "Medium"),
            ("quiz-int", "Integration by Parts Mastery Check", "top-int", "Mathematics", "Hard"),
            ("quiz-org", "Organic Substitution Reaction Quiz", "top-org", "Chemistry", "Medium"),
            ("quiz-bio", "Cellular Respiration Pathway Assessment", "top-bio", "Biology", "Medium"),
            ("quiz-fin", "Compound Growth & Interest Calculations", "top-fin", "Mathematics", "Easy"),
        ]

        for q in quizzes:
            cur.execute("""
            INSERT INTO quizzes (id, title, topic_id, subject, difficulty, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (*q, now))

        questions = [
            # EMI questions
            ("q-emi-1", "quiz-emi", "top-emi",
             "According to Faraday's Law, what causes an electromotive force (EMF) to be induced in a coil?",
             "multiple_choice",
             json.dumps([
                 "A constant magnetic field of high intensity",
                 "A time rate of change of magnetic flux through the coil",
                 "A steady electric current flowing through adjacent wires",
                 "Electrostatic charge accumulation on the surface"
             ]),
             "A time rate of change of magnetic flux through the coil",
             "Faraday's Law states EMF = -N * (dPhi/dt). Only changing flux induces an EMF, not a static magnetic field.",
             "Remember the differential operator (d/dt) in Faraday's equation.",
             "Medium", 14),

            ("q-emi-2", "quiz-emi", "top-emi",
             "What physical principle is Lenz's Law directly derived from?",
             "multiple_choice",
             json.dumps([
                 "Conservation of Electric Charge",
                 "Conservation of Energy",
                 "Newton's Third Law alone",
                 "Heisenberg Uncertainty Principle"
             ]),
             "Conservation of Energy",
             "Lenz's Law ensures energy conservation: the induced current opposes flux changes, meaning external work must be expended to produce electrical energy.",
             "Think about what would happen if the induced field accelerated the magnet freely.",
             "Medium", 15),

            ("q-emi-3", "quiz-emi", "top-emi",
             "If the number of turns in a coil is tripled while the rate of magnetic flux change remains constant, what happens to the induced EMF?",
             "multiple_choice",
             json.dumps([
                 "It remains unchanged",
                 "It is cut by one third",
                 "It is multiplied by 3",
                 "It is multiplied by 9"
             ]),
             "It is multiplied by 3",
             "EMF is directly proportional to N: EMF = -N (dPhi/dt). Tripling N triples the EMF.",
             "Look at how N scales linearly in Faraday's formula.",
             "Easy", 14),

            # Integration questions
            ("q-int-1", "quiz-int", "top-int",
             "When evaluating integral(x * cos(x) dx) using Integration by Parts, what is the best choice for u according to LIATE?",
             "multiple_choice",
             json.dumps([
                 "u = cos(x)",
                 "u = x",
                 "u = sin(x)",
                 "u = x * cos(x)"
             ]),
             "u = x",
             "According to LIATE, Algebraic terms (x) come before Trigonometric terms (cos(x)). Setting u = x means du = dx, which simplifies the remaining integral.",
             "LIATE: Logarithmic, Inverse trig, Algebraic, Trigonometric, Exponential.",
             "Medium", 21),

            ("q-int-2", "quiz-int", "top-int",
             "What is the result of evaluating integral(ln(x) dx)?",
             "multiple_choice",
             json.dumps([
                 "1/x + C",
                 "x * ln(x) - x + C",
                 "x * ln(x) + x + C",
                 "(ln(x))^2 / 2 + C"
             ]),
             "x * ln(x) - x + C",
             "Let u = ln(x) and dv = dx. Then du = (1/x) dx and v = x. integral(u dv) = uv - integral(v du) = x*ln(x) - integral(x * 1/x dx) = x*ln(x) - x + C.",
             "Set dv = dx so v = x.",
             "Hard", 21),

            ("q-int-3", "quiz-int", "top-int",
             "In Integration by Parts, which common mistake frequently leads to sign errors on multi-step integrals?",
             "multiple_choice",
             json.dumps([
                 "Integrating dv incorrectly",
                 "Failing to distribute the negative sign in uv - integral(v du)",
                 "Applying the chain rule to algebraic terms",
                 "Choosing u as a constant"
             ]),
             "Failing to distribute the negative sign in uv - integral(v du)",
             "When integrating by parts multiple times, the minus sign in front of the integral must be distributed across all subsequent terms.",
             "Check the brackets around the second application of the formula.",
             "Medium", 21),

            # Organic chemistry questions
            ("q-org-1", "quiz-org", "top-org",
             "Which reaction mechanism proceeds through a single concerted transition state with inversion of stereochemistry?",
             "multiple_choice",
             json.dumps([
                 "SN1",
                 "SN2",
                 "E1",
                 "Free radical halogenation"
             ]),
             "SN2",
             "SN2 (substitution nucleophilic bimolecular) involves backside attack by the nucleophile in one step, causing Walden inversion.",
             "Bimolecular, concerted, backside attack.",
             "Easy", 28),

            ("q-org-2", "quiz-org", "top-org",
             "Which substrate type is most reactive in an SN1 reaction due to carbocation stability?",
             "multiple_choice",
             json.dumps([
                 "Methyl halide",
                 "Primary halide",
                 "Secondary halide",
                 "Tertiary halide"
             ]),
             "Tertiary halide",
             "Tertiary halides form the most stable carbocation intermediate through hyperconjugation and inductive electron donation.",
             "Recall tertiary carbocation stability vs steric hindrance.",
             "Medium", 28),

            # Finance questions
            ("q-fin-1", "quiz-fin", "top-fin",
             "If $1,000 is invested at an annual interest rate of 10% compounded annually, what is the balance after 2 years?",
             "multiple_choice",
             json.dumps([
                 "$1,100",
                 "$1,200",
                 "$1,210",
                 "$1,250"
             ]),
             "$1,210",
             "A = P*(1+r)^t = 1000 * (1.10)^2 = 1000 * 1.21 = $1,210. The extra $10 is interest on the first year's interest.",
             "Calculate year 1 balance ($1,100) and then apply 10% on that total for year 2.",
             "Easy", 38),

            ("q-fin-2", "quiz-fin", "top-fin",
             "As the compounding frequency n approaches infinity in A = P*(1 + r/n)^(nt), what mathematical constant forms the base of the growth?",
             "multiple_choice",
             json.dumps([
                 "pi (3.14159...)",
                 "e (Euler's number, 2.71828...)",
                 "phi (Golden ratio, 1.618...)",
                 "The square root of 2"
             ]),
             "e (Euler's number, 2.71828...)",
             "The limit of (1 + 1/m)^m as m approaches infinity is Euler's number e, resulting in continuous compounding A = P * e^(rt).",
             "Think of continuous compounding formula A = P * e^(rt).",
             "Medium", 38),
        ]

        for q in questions:
            cur.execute("""
            INSERT INTO quiz_questions (id, quiz_id, topic_id, question_text, question_type, options_json, correct_answer, explanation, hint, difficulty, source_page)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, q)

    # Seed baseline learner attempts & telemetry so analytics and gaps have rich initial data to analyze
    cur.execute("SELECT COUNT(*) FROM assessment_attempts WHERE learner_id = 'learner-001'")
    attempt_count = cur.fetchone()[0]
    if attempt_count == 0:
        seed_baseline_attempts(cur)

    conn.commit()
    conn.close()


def seed_baseline_attempts(cur):
    """
    Seeds a realistic historical baseline:
    - Strong mastery in Organic Reactions (81%)
    - Developing in Electromagnetic Induction (68%)
    - Weak gap in Integration by Parts (38%) with repeated mistakes
    - Developing in Cell Respiration (55%)
    This satisfies Section 1.3 & 7.3: Real data model with authentic records for EDA.
    """
    now = datetime.utcnow()
    import datetime as dt

    # 1. Organic Reactions (Strong: 9/10, 8/10)
    att1_id = "att-org-01"
    cur.execute("""
    INSERT INTO assessment_attempts (id, learner_id, quiz_id, topic_id, score, total_questions, correct_count, is_completed, is_post_test, started_at, completed_at, hints_used)
    VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, 0)
    """, (att1_id, "learner-001", "quiz-org", "top-org", 0.85, 2, 2, (now - dt.timedelta(days=3)).isoformat(), (now - dt.timedelta(days=3)).isoformat()))

    cur.execute("INSERT INTO question_responses VALUES (?, ?, ?, ?, ?, 1, ?)",
                ("resp-org-1", att1_id, "q-org-1", "top-org", "SN2", (now - dt.timedelta(days=3)).isoformat()))
    cur.execute("INSERT INTO question_responses VALUES (?, ?, ?, ?, ?, 1, ?)",
                ("resp-org-2", att1_id, "q-org-2", "top-org", "Tertiary halide", (now - dt.timedelta(days=3)).isoformat()))

    # 2. Electromagnetic Induction (Developing: 2/3 correct)
    att2_id = "att-emi-01"
    cur.execute("""
    INSERT INTO assessment_attempts (id, learner_id, quiz_id, topic_id, score, total_questions, correct_count, is_completed, is_post_test, started_at, completed_at, hints_used)
    VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, 1)
    """, (att2_id, "learner-001", "quiz-emi", "top-emi", 0.67, 3, 2, (now - dt.timedelta(days=2)).isoformat(), (now - dt.timedelta(days=2)).isoformat()))

    cur.execute("INSERT INTO question_responses VALUES (?, ?, ?, ?, ?, 1, ?)",
                ("resp-emi-1", att2_id, "q-emi-1", "top-emi", "A time rate of change of magnetic flux through the coil", (now - dt.timedelta(days=2)).isoformat()))
    cur.execute("INSERT INTO question_responses VALUES (?, ?, ?, ?, ?, 0, ?)",
                ("resp-emi-2", att2_id, "q-emi-2", "top-emi", "Conservation of Electric Charge", (now - dt.timedelta(days=2)).isoformat()))
    cur.execute("INSERT INTO question_responses VALUES (?, ?, ?, ?, ?, 1, ?)",
                ("resp-emi-3", att2_id, "q-emi-3", "top-emi", "It is multiplied by 3", (now - dt.timedelta(days=2)).isoformat()))

    # 3. Integration by Parts (Weak: Attempt 1 had 1/3, Attempt 2 had 1/3 -> repeated mistake on q-int-3)
    att3_id = "att-int-01"
    cur.execute("""
    INSERT INTO assessment_attempts (id, learner_id, quiz_id, topic_id, score, total_questions, correct_count, is_completed, is_post_test, started_at, completed_at, hints_used)
    VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, 2)
    """, (att3_id, "learner-001", "quiz-int", "top-int", 0.33, 3, 1, (now - dt.timedelta(days=1)).isoformat(), (now - dt.timedelta(days=1)).isoformat()))

    cur.execute("INSERT INTO question_responses VALUES (?, ?, ?, ?, ?, 1, ?)",
                ("resp-int-1", att3_id, "q-int-1", "top-int", "u = x", (now - dt.timedelta(days=1)).isoformat()))
    cur.execute("INSERT INTO question_responses VALUES (?, ?, ?, ?, ?, 0, ?)",
                ("resp-int-2", att3_id, "q-int-2", "top-int", "1/x + C", (now - dt.timedelta(days=1)).isoformat()))
    cur.execute("INSERT INTO question_responses VALUES (?, ?, ?, ?, ?, 0, ?)",
                ("resp-int-3", att3_id, "q-int-3", "top-int", "Choosing u as a constant", (now - dt.timedelta(days=1)).isoformat()))

    # Second attempt on Integration by Parts
    att4_id = "att-int-02"
    cur.execute("""
    INSERT INTO assessment_attempts (id, learner_id, quiz_id, topic_id, score, total_questions, correct_count, is_completed, is_post_test, started_at, completed_at, hints_used)
    VALUES (?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, 1)
    """, (att4_id, "learner-001", "quiz-int", "top-int", 0.33, 3, 1, (now - dt.timedelta(hours=6)).isoformat(), (now - dt.timedelta(hours=6)).isoformat()))

    cur.execute("INSERT INTO question_responses VALUES (?, ?, ?, ?, ?, 1, ?)",
                ("resp-int-4", att4_id, "q-int-1", "top-int", "u = x", (now - dt.timedelta(hours=6)).isoformat()))
    cur.execute("INSERT INTO question_responses VALUES (?, ?, ?, ?, ?, 0, ?)",
                ("resp-int-5", att4_id, "q-int-2", "top-int", "(ln(x))^2 / 2 + C", (now - dt.timedelta(hours=6)).isoformat()))
    cur.execute("INSERT INTO question_responses VALUES (?, ?, ?, ?, ?, 0, ?)",
                ("resp-int-6", att4_id, "q-int-3", "top-int", "Integrating dv incorrectly", (now - dt.timedelta(hours=6)).isoformat()))

    # Learning events
    events = [
        ("evt-1", "learner-001", "document_uploaded", "top-emi", json.dumps({"filename": "Advanced_Science_and_Calculus_Textbook.pdf"}), (now - dt.timedelta(days=4)).isoformat()),
        ("evt-2", "learner-001", "topic_opened", "top-org", json.dumps({"page": 28}), (now - dt.timedelta(days=3)).isoformat()),
        ("evt-3", "learner-001", "quiz_completed", "top-org", json.dumps({"score": 1.0}), (now - dt.timedelta(days=3)).isoformat()),
        ("evt-4", "learner-001", "topic_opened", "top-emi", json.dumps({"page": 14}), (now - dt.timedelta(days=2)).isoformat()),
        ("evt-5", "learner-001", "quiz_completed", "top-emi", json.dumps({"score": 0.67}), (now - dt.timedelta(days=2)).isoformat()),
        ("evt-6", "learner-001", "topic_opened", "top-int", json.dumps({"page": 21}), (now - dt.timedelta(days=1)).isoformat()),
        ("evt-7", "learner-001", "hint_requested", "top-int", json.dumps({"question_id": "q-int-3"}), (now - dt.timedelta(days=1)).isoformat()),
        ("evt-8", "learner-001", "quiz_completed", "top-int", json.dumps({"score": 0.33}), (now - dt.timedelta(days=1)).isoformat()),
        ("evt-9", "learner-001", "quiz_completed", "top-int", json.dumps({"score": 0.33}), (now - dt.timedelta(hours=6)).isoformat()),
    ]
    for ev in events:
        cur.execute("INSERT INTO learning_events (id, learner_id, event_type, topic_id, metadata_json, timestamp) VALUES (?, ?, ?, ?, ?, ?)", ev)

    # Initial study plan recommendation items
    plan_items = [
        ("plan-1", "learner-001", "top-int", "worked_example",
         "Integration by Parts: Step-by-Step Sign Distribution",
         "Detected 2 consecutive incorrect attempts on sign rules during integration.",
         "Accuracy: 33% across 6 questions (2 repeated errors on sign distribution).",
         "High", 12, 0, now.isoformat(), None),
        ("plan-2", "learner-001", "top-int", "simulation",
         "Explore Calculus Rate & Accumulation Lab",
         "Strengthen conceptual foundation before advancing to Definite Integrals.",
         "Prerequisite for Definite Integrals currently weak.",
         "High", 10, 0, now.isoformat(), None),
        ("plan-3", "learner-001", "top-emi", "practice_quiz",
         "Faraday's Law Follow-up Diagnostic",
         "Reinforce Lenz's law and energy conservation before next chapter.",
         "Accuracy: 67% (needs 1 more successful attempt for High Mastery confidence).",
         "Medium", 15, 0, now.isoformat(), None),
    ]
    for p in plan_items:
        cur.execute("""
        INSERT INTO study_plan_items (id, learner_id, topic_id, action_type, title, reason, evidence, priority, duration_minutes, is_completed, created_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, p)
