# db-troubleshooting-agent

A RAG agent that answers PostgreSQL questions from the official docs, plus a
read-only SQL tool over a sample table. Vertex AI + Cloud SQL (pgvector) +
Cloud Run.

I do enterprise database support for a living. I built this to see where agent
tooling actually falls over in a corporate setup, instead of reading about it.

## Architecture

```
POST /ask
  -> Cloud Run (FastAPI), runs as db-agent-sa
  -> Gemini 2.5 Flash with two tools:
       search_docs()        -> pgvector similarity search on Cloud SQL
       run_readonly_query() -> Cloud SQL as agent_ro
```

One Cloud SQL instance does both jobs: it holds the `vector(768)` column with an
HNSW index, and it's what the SQL tool queries.

## Data

Public PostgreSQL 16 docs only. The corpus isn't in the repo. `fetch_docs.py`
pulls and cleans the pages, so you can rebuild it. Nothing internal or
customer-related goes anywhere near this.

## Setup

```bash
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
python fetch_docs.py
python ingest.py
python agent.py          # smoke test
uvicorn main:app         # http://127.0.0.1:8000/docs
```

`schema.sql` creates the tables, the HNSW index, 5000 rows of fake orders, and
the `agent_ro` role. `.env` holds the connection details.

## Notes on the SQL tool

Letting a model emit SQL that you then execute is the obvious way to get burned,
so there are two layers:

In the app, `run_readonly_query` rejects anything that isn't a single SELECT,
blocks a keyword denylist, and requires the query to hit an allowlisted table.

In the database, it connects as `agent_ro`: SELECT on two tables, nothing else,
`statement_timeout = 5s`. If the app-side checks are wrong, the role still can't
do damage.

The smoke test in `agent.py` includes "Delete every row in sample_orders" and
expects a rejection.

## Why Vertex AI and not the API-key backend

Same SDK, one flag. The API-key path is easier and I'd have finished sooner, but
there's no IAM, no region pinning, no audit log. Fine for a demo, not something
you'd get past a security review.

## Things that broke

**Billing wasn't linked, and it looked like six separate problems.** API enable
failed with FAILED_PRECONDITION, instance create failed with a permissions error,
`sql users set-password` returned 403, secret create failed again with
FAILED_PRECONDITION. Four different messages, one cause. The setup script now
checks `billingEnabled` first and exits if it's false.

**Cloud Run wouldn't take my Gmail as the runtime identity.**
`Unsupported service account: <email>`. Needed a service account. Obvious in
hindsight.

**A 404 left an env var empty and the deploy still succeeded.** I built
`--set-env-vars` from a shell variable filled by `gcloud sql instances describe`.
Wrong instance name, 404, variable became `""`. `INSTANCE_CONNECTION_NAME=` went
out empty, deploy reported success, and it only showed up as a connection failure
at request time. Now I echo the derived values and check them before deploying.

**Both DB roles had the same password.** I made `agent_ro` specifically so the
agent couldn't write, then gave it the same password as `postgres`. Pointless.

**Secrets in git history.** The setup script had real passwords and was already
committed. Editing it and committing again doesn't help. Hadn't pushed yet, so I
dropped the local history, gitignored the script, and rotated everything.

## Known gaps

- No eval set. I judged retrieval quality by reading answers, which is not a
  measurement.
- Chunking is fixed 1200 chars with 150 overlap. It splits mid-sentence and
  sometimes mid-table. Haven't tried anything smarter.
- Cloud SQL is on a public IP. Should be private IP + VPC-SC.
- Password auth to the database. IAM database auth would remove the secret
  instead of managing it.
- Tool calls aren't logged anywhere. No way to audit what the agent actually ran.
- Tested with maybe 20 questions total.

## Cost

The `db-f1-micro` instance is the only thing that bills continuously. Stop it when
you're not using it:

```bash
gcloud sql instances patch db-agent-pg-jy --activation-policy=NEVER
```