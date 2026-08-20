import os, re, time
import requests
from bs4 import BeautifulSoup

BASE = "https://www.postgresql.org/docs/16"

PAGES = {
    "postgresql-explicit-locking":    "explicit-locking.html",
    "postgresql-mvcc-intro":          "mvcc-intro.html",
    "postgresql-transaction-iso":     "transaction-iso.html",
    "postgresql-monitoring-stats":    "monitoring-stats.html",
    "postgresql-routine-vacuuming":   "routine-vacuuming.html",
    "postgresql-autovacuum-config":   "runtime-config-autovacuum.html",
    "postgresql-using-explain":       "using-explain.html",
    "postgresql-planner-stats":       "planner-stats.html",
    "postgresql-performance-tips":    "performance-tips.html",
    "postgresql-indexes-types":       "indexes-types.html",
    "postgresql-resource-config":     "runtime-config-resource.html",
    "postgresql-wal-configuration":   "wal-configuration.html",
    "postgresql-connection-config":   "runtime-config-connection.html",
    "postgresql-error-codes":         "errcodes-appendix.html",
}

os.makedirs("docs", exist_ok=True)
session = requests.Session()
session.headers["User-Agent"] = "personal-learning-project/1.0"

for name, path in PAGES.items():
    url = f"{BASE}/{path}"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    for tag in soup.select("[class*=nav], #docNav, #pgFooter, #pgHeader"):
        tag.decompose()

    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text).strip()

    out = f"docs/{name}.txt"
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"Source: {url}\n\n{text}")

    print(f"{name:35s} {len(text):>7,} chars")
    time.sleep(1)          # 서버에 부담 주지 않기

print("\nDone.")