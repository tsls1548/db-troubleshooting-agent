import os, re, glob
from dotenv import load_dotenv
from google import genai
import sqlalchemy
from db import admin_engine

load_dotenv()

EMBED_MODEL = "text-embedding-004"
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150
BATCH = 20

client = genai.Client(
    vertexai=True,
    project=os.environ["GCP_PROJECT"],
    location=os.environ["GCP_LOCATION"],
)


def chunk_text(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    step = CHUNK_SIZE - CHUNK_OVERLAP
    out = []
    for i in range(0, len(text), step):
        piece = text[i : i + CHUNK_SIZE].strip()
        if len(piece) > 100:
            out.append(piece)
    return out


def embed(texts: list[str]) -> list[list[float]]:
    resp = client.models.embed_content(model=EMBED_MODEL, contents=texts)
    return [e.values for e in resp.embeddings]


def to_vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.7f}" for v in values) + "]"


def main() -> None:
    engine = admin_engine()
    files = sorted(glob.glob("docs/*.txt"))
    if not files:
        raise SystemExit("docs/ 폴더에 .txt 파일이 없습니다.")

    stmt = sqlalchemy.text(
        "INSERT INTO doc_chunks (source, title, content, embedding) "
        "VALUES (:source, :title, :content, CAST(:embedding AS vector))"
    )

    total = 0
    with engine.connect() as conn:
        for path in files:
            title = os.path.splitext(os.path.basename(path))[0]
            with open(path, encoding="utf-8") as f:
                chunks = chunk_text(f.read())

            for i in range(0, len(chunks), BATCH):
                batch = chunks[i : i + BATCH]
                vectors = embed(batch)
                conn.execute(
                    stmt,
                    [
                        {
                            "source": path.replace("\\", "/"),
                            "title": title,
                            "content": c,
                            "embedding": to_vector_literal(v),
                        }
                        for c, v in zip(batch, vectors)
                    ],
                )
                conn.commit()
            total += len(chunks)
            print(f"{title}: {len(chunks)} chunks")

    print(f"\n총 {total} chunks 색인 완료")


if __name__ == "__main__":
    main()