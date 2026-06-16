# database.py
import sqlite3
import os

DB_NAME = "azota_production.db"

def init_db():
    """Initializes the SQLite database and creates the tables based on the ERD."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            subject TEXT NOT NULL,
            file_blob BLOB,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    # print(f"✨ Success: Database '{DB_NAME}' and tables initialized perfectly!")

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

def insert_exam_file(exam_name, subject, file_bytes):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO exam_files (name, subject, file_blob)
        VALUES (?, ?, ?)
    """, (exam_name, subject, file_bytes))

    conn.commit()
    conn.close()

def update_exam_file(exam_id: int, file_bytes: bytes) -> None:
    """Replace the file_blob of an existing exam_files row."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE exam_files SET file_blob = ? WHERE id = ?", (file_bytes, exam_id))
    conn.commit()
    conn.close()


def list_exam_files():
    """Return all saved answer keys as [(id, name, subject, uploaded_at), ...]."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, subject, uploaded_at FROM exam_files ORDER BY uploaded_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_exam_file(file_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, subject, file_blob
        FROM exam_files
        WHERE id = ?
    """, (file_id,))

    row = cursor.fetchone()
    conn.close()

    return row

if __name__ == "__main__":
    init_db()