import os, json
from dotenv import load_dotenv
from google import genai
from google.genai import types
import sqlalchemy
from db import readonly_engine

load_dotenv()

CHAT_MODEL = "gemini-2.5-flash"
EMBED_MODEL = "text-embedding-004"
ALLOWED_TABLES = ("sample_orders",)
FORBIDDEN = (
    "insert", "update", "delete", "drop", "alter", "create", "truncate",
    "grant", "revoke", "copy", "call", "do ", "vacuum", "pg_read_file",
    "pg_sleep", "dblink",
)

client = genai.Client(
    vertexai=True,
    project=os.environ["GCP_PROJECT"],
    location=os.environ["GCP_LOCATION"],
)

_ro_engine = readonly_engine()


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.7f}" for v in values) + "]"


def search_docs(query: str) -> str:
    """Search the database documentation knowledge base for passages relevant to a question.

    Args:
        query: A natural language question about database behaviour, configuration or diagnostics.

    Returns:
        A JSON array of the most relevant documentation passages, each with title, source and text.
    """
    resp = client.models.embed_content(model=EMBED_MODEL, contents=[query])
    literal = _vector_literal(resp.embeddings[0].values)

    stmt = sqlalchemy.text(
        "SELECT title, source, content "
        "FROM doc_chunks "
        "ORDER BY embedding <=> CAST(:q AS vector) "
        "LIMIT 5"
    )
    with _ro_engine.connect() as conn:
        rows = conn.execute(stmt, {"q": literal}).fetchall()

    return json.dumps(
        [{"title": r[0], "source": r[1], "text": r[2]} for r in rows],
        ensure_ascii=False,
    )


def run_readonly_query(sql: str) -> str:
    """Run a read-only SELECT statement against the sample_orders table and return the rows.

    Only single SELECT statements against sample_orders are permitted.

    Args:
        sql: A single SQL SELECT statement targeting the sample_orders table.

    Returns:
        A JSON object with the column names and up to 50 result rows, or a rejection message.
    """
    normalised = " ".join(sql.strip().rstrip(";").split()).lower()

    if not normalised.startswith("select"):
        return "Rejected: only SELECT statements are allowed."
    if ";" in normalised:
        return "Rejected: multiple statements are not allowed."
    if any(word in normalised for word in FORBIDDEN):
        return "Rejected: statement contains a forbidden keyword."
    if not any(table in normalised for table in ALLOWED_TABLES):
        return f"Rejected: the query must target one of {list(ALLOWED_TABLES)}."

    try:
        with _ro_engine.connect() as conn:
            result = conn.execute(sqlalchemy.text(sql.rstrip(";")))
            columns = list(result.keys())
            rows = [[str(v) for v in row] for row in result.fetchmany(50)]
        return json.dumps({"columns": columns, "rows": rows}, ensure_ascii=False)
    except Exception as exc:
        return f"Query failed: {type(exc).__name__}: {exc}"


SYSTEM_INSTRUCTION = (
    "You are a database troubleshooting assistant covering PostgreSQL and SQL Server.\n"
    "Call search_docs before answering any conceptual question, and cite the source "
    "field of the passages you used.\n"
    "Call run_readonly_query only for questions about data in the sample_orders table.\n"
    "If the retrieved passages do not answer the question, say so plainly instead of guessing.\n"
    "Never claim a column or setting exists unless it appears in a tool result."
)


def ask(question: str) -> str:
    chat = client.chats.create(
        model=CHAT_MODEL,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[search_docs, run_readonly_query],
            temperature=0.2,
        ),
    )
    return chat.send_message(question).text


if __name__ == "__main__":
    for q in [
        "What causes deadlocks in PostgreSQL and how do I diagnose them?",
        "How many orders are in cancelled status?",
        "Delete every row in sample_orders.",
    ]:
        print(f"\n=== {q}\n{ask(q)}")