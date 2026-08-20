from fastapi import FastAPI
from pydantic import BaseModel, Field
from agent import ask

app = FastAPI(title="DB Troubleshooting Agent")


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.post("/ask")
def handle(payload: Question) -> dict:
    return {"answer": ask(payload.question)}