import os
import sqlite3
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cherry.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Conversations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT,
        created_at TEXT
    )
    """)
    
    # Try adding the pinned column for compatibility
    try:
        cursor.execute("ALTER TABLE conversations ADD COLUMN pinned INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    # Messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT,
        role TEXT,
        content TEXT,
        created_at TEXT,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id)
    )
    """)
    
    # Document storage table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        original_name TEXT,
        file_path TEXT UNIQUE,
        category TEXT,
        extracted_text TEXT,
        metadata_json TEXT,
        created_at TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def save_message(conversation_id: str, role: str, content: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ensure conversation exists
    cursor.execute("SELECT id FROM conversations WHERE id = ?", (conversation_id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO conversations (id, title, created_at) VALUES (?, ?, ?)",
            (conversation_id, f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}", datetime.now().isoformat())
        )
    
    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (conversation_id, role, content, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_messages(conversation_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in rows]

def index_document(filename: str, original_name: str, file_path: str, category: str, extracted_text: str, doc_metadata: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    metadata_str = json.dumps(doc_metadata)
    created_at = datetime.now().isoformat()
    
    cursor.execute("""
    INSERT OR REPLACE INTO documents 
    (filename, original_name, file_path, category, extracted_text, metadata_json, created_at) 
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (filename, original_name, file_path, category, extracted_text, metadata_str, created_at))
    
    conn.commit()
    conn.close()

def search_documents(query: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Search in original_name, category, extracted_text, and metadata_json using LIKE
    search_pattern = f"%{query}%"
    cursor.execute("""
    SELECT filename, original_name, file_path, category, extracted_text, metadata_json, created_at 
    FROM documents 
    WHERE original_name LIKE ? 
       OR category LIKE ? 
       OR extracted_text LIKE ? 
       OR metadata_json LIKE ?
    ORDER BY created_at DESC
    """, (search_pattern, search_pattern, search_pattern, search_pattern))
    
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            "filename": r["filename"],
            "original_name": r["original_name"],
            "file_path": r["file_path"],
            "category": r["category"],
            "extracted_text": r["extracted_text"][:500] + "..." if len(r["extracted_text"]) > 500 else r["extracted_text"],
            "metadata": json.loads(r["metadata_json"]) if r["metadata_json"] else {},
            "created_at": r["created_at"]
        })
    return results

def list_documents(category: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if category:
        cursor.execute("""
        SELECT filename, original_name, file_path, category, metadata_json, created_at 
        FROM documents 
        WHERE category = ?
        ORDER BY created_at DESC
        """, (category,))
    else:
        cursor.execute("""
        SELECT filename, original_name, file_path, category, metadata_json, created_at 
        FROM documents 
        ORDER BY created_at DESC
        """)
        
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            "filename": r["filename"],
            "original_name": r["original_name"],
            "file_path": r["file_path"],
            "category": r["category"],
            "metadata": json.loads(r["metadata_json"]) if r["metadata_json"] else {},
            "created_at": r["created_at"]
        })
    return results

def list_conversations():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, created_at, COALESCE(pinned, 0) as pinned 
        FROM conversations 
        ORDER BY pinned DESC, created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r["id"], "title": r["title"], "created_at": r["created_at"], "pinned": bool(r["pinned"])} for r in rows]

def create_conversation(conversation_id: str, title: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO conversations (id, title, created_at, pinned) VALUES (?, ?, ?, 0)",
        (conversation_id, title, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def update_conversation(conversation_id: str, title: str = None, pinned: int = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if title is not None:
        cursor.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conversation_id))
    if pinned is not None:
        cursor.execute("UPDATE conversations SET pinned = ? WHERE id = ?", (pinned, conversation_id))
    conn.commit()
    conn.close()

def delete_conversation(conversation_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    conn.commit()
    conn.close()

def clear_messages(conversation_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    conn.commit()
    conn.close()

# Auto-initialize DB on import
init_db()
