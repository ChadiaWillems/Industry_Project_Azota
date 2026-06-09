# database.py
import sqlite3
import os

DB_NAME = "azota_production.db"

def init_db():
    """Initializes the SQLite database and creates the tables based on the ERD."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Enable Foreign Key support in SQLite (disabled by default)
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # 1. Parent Table: SCANS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            score_earned INTEGER,
            score_total INTEGER,
            img_raw TEXT,
            img_standardized TEXT,
            img_sections TEXT,
            img_graded TEXT
        )
    """)
    
    # 2. Child Table: DETECTED_ANSWERS (Without correct_solution, matching the Excel logic)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detected_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER,
            question_number INTEGER,
            ai_detected TEXT,
            teacher_corrected TEXT,
            is_correct INTEGER, -- 1 = true, 0 = false
            FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"✨ Success: Database '{DB_NAME}' and tables initialized perfectly!")

# =====================================================================
# BACKEND & FRONTEND HELPER FUNCTIES
# =====================================================================

def insert_new_scan(score_earned, score_total, img_raw, img_standardized, img_sections, img_graded, answers_list):
    """
    Saves a complete scan and its corresponding answers.
    answers_list should be a list of dicts: [{'question': 1, 'ai': 'A', 'is_correct': 1}, ...]
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    cursor.execute("""
        INSERT INTO scans (score_earned, score_total, img_raw, img_standardized, img_sections, img_graded)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (score_earned, score_total, img_raw, img_standardized, img_sections, img_graded))
    
    scan_id = cursor.lastrowid
    
    for ans in answers_list:
        cursor.execute("""
            INSERT INTO detected_answers (scan_id, question_number, ai_detected, teacher_corrected, is_correct)
            VALUES (?, ?, ?, ?, ?)
        """, (scan_id, ans['question'], ans['ai'], ans['ai'], ans['is_correct']))
        
    conn.commit()
    conn.close()
    return scan_id

def get_scan_answers(scan_id):
    """Fetches all answers for a specific scan to show in the Streamlit table."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT question_number, ai_detected, teacher_corrected, is_correct 
        FROM detected_answers 
        WHERE scan_id = ?
        ORDER BY question_number ASC
    """, (scan_id,))
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {"Question": r[0], "AI Detected": r[1], "Corrected Input": r[2], "Is Correct": bool(r[3])}
        for r in rows
    ]

if __name__ == "__main__":
    init_db()