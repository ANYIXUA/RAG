"""临时只读探针：确认 PostgreSQL 可用性与冻结语料一致性。"""
import json
import re
import sys

env = {}
for line in open(".env", encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env[k.strip()] = v.strip()

base = env["RAG_OPS_POSTGRES_DSN"]
import psycopg

for host, port in [("127.0.0.1", 15432), ("127.0.0.1", 5432), ("localhost", 15432)]:
    cand = re.sub(r"@postgres:\d+/", "@%s:%d/" % (host, port), base)
    try:
        with psycopg.connect(cand, connect_timeout=5) as c:
            with c.cursor() as cur:
                cur.execute(
                    "select count(*) from rag_knowledge_chunks "
                    "where collection_name='default' and status='active'"
                )
                n = cur.fetchone()[0]
                cur.execute(
                    "select count(distinct document_id) from rag_knowledge_chunks "
                    "where collection_name='default' and status='active'"
                )
                d = cur.fetchone()[0]
                cur.execute(
                    "select chunk_id, md5(chunk_text), metadata->>'content_hash' "
                    "from rag_knowledge_chunks where collection_name='default' "
                    "and status='active' order by chunk_id"
                )
                rows = cur.fetchall()
        print("OK", host, port, "active_chunks", n, "docs", d)
        print("DB_DSN_REDACTED", re.sub(r":([^:@/]+)@", ":***@", cand))
        # 与冻结语料比对
        frozen = {}
        for line in open(
            "storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl", encoding="utf-8"
        ):
            r = json.loads(line)
            frozen[r["chunk_id"]] = r["chunk_text"]
        print("frozen", len(frozen), "db", len(rows))
        db_ids = {r[0] for r in rows}
        print("id_sets_equal", db_ids == set(frozen))
        print("only_in_db", len(db_ids - set(frozen)), "only_in_frozen", len(set(frozen) - db_ids))

        mismatch = 0
        texts = {}
        with psycopg.connect(cand, connect_timeout=5) as c:
            with c.cursor() as cur:
                cur.execute(
                    "select chunk_id, chunk_text from rag_knowledge_chunks "
                    "where collection_name='default' and status='active'"
                )
                for cid, text in cur.fetchall():
                    texts[cid] = text
        for cid, text in frozen.items():
            if cid in texts and texts[cid] != text:
                mismatch += 1
        print("text_mismatch_count", mismatch)
        break
    except Exception as e:
        print("FAIL", host, port, type(e).__name__, str(e)[:300])
