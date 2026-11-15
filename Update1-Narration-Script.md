# AgriConnect AI — Update #1 Video Narration Script

**Target length:** ~8–9 minutes (requirement is 7+).
**Order (do not change):** Slides → Demo → Code.
**Legend:** plain text = read aloud · `[ACTION]` = what to do on screen · *(~time)* = running clock.

**Before you press record:** reseed clean data and restart the server, close the Lab 4 tab,
have the PPTX open, and have both **Customer chat** and **Staff inbox** tabs ready on the port it printed (e.g. 8000 or 8002).

---

## PART 1 — SLIDES  *(target 0:00 – 1:50)*

`[Share full screen. Open AgriConnect-Progress-Update-1.pptx and press F5 for presentation mode — Slide 1.]`

> Hi, I'm Edel Kiprop, and this is Progress Update #1 for AgriConnect AI — a customer-support
> platform for agricultural input suppliers. The assistant answers from approved supplier
> documents and a live product catalog, and hands off to staff when it should.

`[Next — Slide 2, "Progress at a glance".]`

> Here's where things stand. I'll demo the features in this order. Five are working and
> integrated in one codebase: the web chat with saved history, grounded answers over documents,
> staff takeover, the product-lookup tool, and multi-tenant isolation. Three are in progress —
> document upload, logging and counts, and the evaluation benchmark — and basic contact records
> is still to start.

`[Next — Slide 3, the Update #1 feature table.]`

> These are the four features due for this update. For each one, the "work done this update"
> column shows exactly what I built: the chat with saved history and citations, retrieval-grounded
> answers that abstain when the evidence is weak, the staff inbox and takeover, and the first
> version of the evaluation test suite.

`[Next — Slide 4, remaining core features.]`

> The rest of the planned scope — the product tool, which is done, plus upload, contact records,
> logging, and the multi-tenant isolation that's also done — shown here so the full picture is clear.

`[Next — Slide 5, work breakdown.]`

> This is a solo project, so I own all nine features.

`[Next — Slide 6, then press Esc to exit the slideshow.]`

> And next up for Update #2 is swapping retrieval to real embeddings and comparing configurations.
> Now let me show it running live.

---

## PART 2 — DEMO  *(target 1:50 – 4:50)*

`[Switch to the browser tab at the customer chat URL the server printed. Set the Supplier dropdown to "GreenHarvest Agri Supplies".]`

> This is the customer chat for GreenHarvest, one of two suppliers in the system. It's all one
> running application — one FastAPI app, one database, no switching between tools or branches.

`[Click "Start chat".]`

> I'll start a conversation and ask a question that should be answered from the supplier's documents.

`[Type: What spacing do you recommend for hybrid maize?  — press Enter, wait for the reply.]`

> There's the answer — and notice it cites its source: "Maize Seed Planting Guide." The chips
> underneath show the tool it used and the document it pulled from. It only answers from approved
> content, so the answer is grounded and traceable.

`[Type: How much is NPK 23:23:0 and is it in stock?  — Enter.]`

> This time it recognized a price-and-stock question and called the product-lookup tool. It's
> returning the exact price and the live stock level straight from the catalog — not from a document.

`[Type: Is DAP fertilizer in stock?  — Enter.]`

> And it reports out-of-stock items honestly.

`[Type: What will the weather be next week?  — Enter.]`

> Now here's an important behavior. The weather isn't in any approved document, so instead of
> guessing, the assistant abstains and hands the conversation to a staff member. Abstaining when
> there's no evidence is exactly what a production assistant needs to do.

`[Type: I'd like to speak to a human.  — Enter.]`

> A customer can also ask for a person directly, and it hands off right away, carrying the context.

`[Switch to the "Staff inbox" tab. Set Supplier to "GreenHarvest". Click the waiting conversation.]`

> This is the staff side. The handed-off conversation is waiting, tagged with the reason. When I
> open it, the staff member sees the whole thread — and, importantly, "what the assistant checked":
> the documents it retrieved and their similarity scores. So the handoff carries real context.

`[Type a reply in the box, e.g.: Hi Jane, happy to help with that — I'll check and get right back to you.  Click "Send as staff".]`

> I'll reply as staff...

`[Switch back to the Customer chat tab — the staff reply is there.]`

> ...and the reply lands in the same conversation the customer is already in. One shared thread
> between the assistant and staff.

`[In the chat, change Supplier to "FarmDirect Co-op", Start chat, type: How much is Shangi potato seed?  — Enter.]`

> Last, multi-tenant isolation. FarmDirect is a different supplier with its own catalog — it stocks
> Shangi potato seed.

`[Change Supplier back to "GreenHarvest", Start chat, type the same: How much is Shangi potato seed?  — Enter.]`

> But GreenHarvest doesn't carry that product, so it says so and hands off. Each supplier only ever
> sees its own catalog, documents, and conversations — and the server rejects any cross-tenant
> request. Now let me show the code behind this.

---

## PART 3 — CODE WALKTHROUGH  *(target 4:50 – 8:15, aim 3+ minutes)*

`[Switch to VS Code. Open agriconnect/main.py.]`

> The whole thing is one FastAPI application. This is the API boundary. Every request that touches
> data goes through these two helpers — `require_tenant` and `require_conversation`. This is where
> tenant isolation is enforced: if a request asks for a conversation that belongs to another
> supplier, it returns a 403 instead of any data. That's the single place that guarantees one
> tenant can't read another's.

`[Open agriconnect/agent.py. Scroll to run_agent.]`

> This is the agent. For each customer message it decides what to do, within a fixed step budget.
> First, if the customer explicitly asks for a human, it hands off. Next, if it's a price or stock
> question, it calls the product-lookup tool against the catalog. Otherwise it goes to document
> retrieval. And this is the abstention gate: if the best evidence is too weak, it refuses to answer
> and hands off instead. That abstention logic is what keeps it from making things up.

`[Open agriconnect/retrieval.py.]`

> This is the retrieval — the RAG part. It builds a per-tenant index over the document chunks and
> returns the best-matching passages for a query. I'm using TF-IDF similarity here so it runs with
> no external services, but `search` is the one function I'll swap for real embeddings and pgvector
> in the next update — nothing else in the app has to change.

`[Open agriconnect/llm.py.]`

> This generates the grounded answer. It's constrained to only the retrieved sources and cites them,
> and it's built to abstain if the sources don't actually contain the answer. It runs fully offline
> by default, and automatically uses a hosted model if an API key is provided.

`[Open agriconnect/db.py.]`

> And the data layer is SQLite. The thing to notice is that every table carries a tenant_id, and
> every query filters by it — that's what makes the isolation in the API layer real all the way down.

`[Optional — open agriconnect/static/app.js briefly.]`

> The front end is a lightweight chat UI served by the same app; it polls for new messages, which is
> how a staff reply shows up in the customer's window.

> So to summarize: this update delivers a working, integrated slice — retrieval-grounded answers
> with citations and abstention, a catalog tool, staff handoff that carries context, and enforced
> multi-tenant isolation — all in one codebase. Thanks for watching.

`[Stop recording.]`

---

### Quick checklist
- [ ] Reseeded clean data, server restarted, Lab 4 tab closed
- [ ] Mic on, correct screen captured (do a 10-second test take first)
- [ ] Slides → Demo → Code, in that order
- [ ] Code section runs at least 3 minutes
- [ ] Total over 7 minutes
- [ ] Upload to YouTube as **Unlisted**; submit the link + the PPTX
