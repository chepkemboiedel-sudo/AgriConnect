# AgriConnect AI — Update #1 demo slice

A single, integrated customer-support platform for agricultural input suppliers.
The assistant answers from **approved supplier documents** and a **live product
catalog**, cites its sources, **abstains** when it isn't sure, and **hands off to
staff** with the full conversation and the evidence it checked — all with
**per-tenant isolation**.

> One codebase, one process, one command to run. No branch/emulator switching.

---

## 1. Run it (Windows, ~30 seconds)

```powershell
cd "Agri Connect"
./run.ps1
```

`run.ps1` installs the two dependencies (`fastapi`, `uvicorn`), seeds the sample
database on first run, and starts the server. It prints the URLs — it
auto-selects a free port (8000, or the next open one):

- **Customer chat:** `http://127.0.0.1:8000/`
- **Staff inbox:**   `http://127.0.0.1:8000/inbox`

Prefer manual steps?

```powershell
python -m pip install -r requirements.txt
python -m agriconnect.seed      # create/reset the sample data (optional)
python -m agriconnect           # start the server
```

To reset the data to a clean state before recording: `python -m agriconnect.seed`.

### Optional: use a real LLM
The app runs **fully offline** by default (local TF-IDF retrieval + extractive,
cited answers). To have answers written by a model instead, copy `.env.example`
to `.env` and add your own `OPENAI_API_KEY`. Nothing else changes; the provider
chip in the header switches from `local` to `openai`. Your key stays in `.env`
(git-ignored) and is only sent to the provider you choose.

---

## 2. Demo script (follow your overview-slide order)

Open the **customer chat**, pick **GreenHarvest Agri Supplies**, start a chat as
"Jane", then:

| # | Say this | What it shows |
|---|----------|---------------|
| 1 | `What spacing do you recommend for hybrid maize?` | **Grounded answer** from a document, with a *(Source: …)* citation and source chips |
| 2 | `How much is NPK 23:23:0 and is it in stock?` | **Product-lookup tool** — exact price + live stock from the catalog |
| 3 | `Is DAP fertilizer in stock?` | Tool returns an **out-of-stock** item honestly |
| 4 | `Can I return opened fertilizer for a refund?` | Grounded answer from the **returns policy** doc |
| 5 | `What will the weather be next week?` | **Abstention → handoff** (no approved evidence) |
| 6 | `I'd like to speak to a human about a bulk order.` | **Explicit handoff** request |

Now open the **staff inbox** (new tab), pick **GreenHarvest**:
- The conversation is waiting, tagged with the **reason** for handoff.
- Open it: you see the **whole thread** plus **"What the assistant checked"**
  (the retrieved sources and similarity scores).
- Type a reply and **Send as staff** — switch back to the chat tab and the
  staff reply appears in the **same** conversation.

**Multi-tenant isolation** (strong moment): in the chat, switch the supplier to
**FarmDirect Co-op**, start a new chat, and ask
`How much is Shangi potato seed?` → FarmDirect **has** it. Switch back to
**GreenHarvest** and ask the same → it is **not in that catalog**, so the
assistant says so and hands off. Each supplier only ever sees its own catalog,
documents, and conversations (the API returns **403** on any cross-tenant read).

---

## 3. Code walkthrough guide (for the video, ~3 min)

Everything lives under `agriconnect/`. Suggested path to talk through:

| File | What to explain |
|------|-----------------|
| `main.py` | The **FastAPI boundary**. `require_tenant` / `require_conversation` enforce tenant access on every data route — this is where isolation lives (cross-tenant → 403). |
| `agent.py` | The **agent** (`run_agent`): human-request → handoff; product/price → catalog tool; else → document retrieval with a **fixed step budget** and an **abstention gate**. |
| `retrieval.py` | **Retrieval** — a per-tenant TF-IDF + cosine index over document chunks. `search()` is the single seam we'll swap for embeddings + pgvector later. |
| `llm.py` | **Grounded answer generation** that adapts: OpenAI (constrained to the sources) if a key is set, otherwise a cited extractive answer. |
| `db.py` | SQLite schema + access helpers. Every table carries `tenant_id`; every query filters by it. |
| `seed.py` | Synthetic data: 2 tenants, 50 catalog products, 8 original supplier documents (chunked). |
| `static/` | The chat UI (`index.html` / `app.js`) and staff inbox (`inbox.html` / `inbox.js`). |

Good concepts to name on camera: **RAG** (retrieve → ground → cite),
**abstention** (coverage + similarity gate before answering), **tool use**
(catalog lookup vs. document retrieval), **handoff with context**, and
**tenant isolation** at the API boundary.

---

## 4. How this maps to the proposal

This slice is faithful to the proposed architecture, with pragmatic choices so
it runs anywhere for Update #1:

| Proposal (production target) | Update #1 slice | Why |
|------|------|-----|
| Next.js + TypeScript UI | Static UI served by FastAPI | One process, nothing to build, easy to demo |
| PostgreSQL + pgvector | SQLite + in-process TF-IDF | Zero install on Windows; `search()` is a clean swap point |
| Hosted LLM + embeddings | Local by default, OpenAI if a key is set | Demo never blocks on an API key or quota |

**Planned next (Update #2):** swap retrieval to real embeddings + pgvector,
compare *model-only vs. retrieval vs. retrieval+tools* on a labelled benchmark,
and report accuracy and model spend.

---

## 5. What's intentionally out of scope for now
Real authentication (staff "login" is a name field), WhatsApp/email/voice
channels, orders/payments, and advanced analytics — all listed as future work in
the proposal.

---

### Project layout
```
Agri Connect/
├─ agriconnect/
│  ├─ main.py          FastAPI app + tenant boundary + routes
│  ├─ agent.py         routing, tools, abstention, handoff
│  ├─ retrieval.py     per-tenant TF-IDF retrieval (RAG seam)
│  ├─ llm.py           grounded answer (local or OpenAI)
│  ├─ db.py            SQLite schema + tenant-scoped access
│  ├─ seed.py          sample tenants / catalog / documents
│  ├─ __main__.py      `python -m agriconnect` launcher
│  └─ static/          chat + staff inbox UIs
├─ requirements.txt
├─ .env.example        copy to .env to enable a real LLM
└─ run.ps1             one-command launcher
```
