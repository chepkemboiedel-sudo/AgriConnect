"""The AgriConnect agent.

For each customer turn the agent:
  1. Checks for an explicit request for a human  -> hand off.
  2. Routes product/stock/price questions to the catalog tool.
  3. Otherwise retrieves approved-document evidence and answers from it,
     abstaining (and handing off) when the evidence is too weak.

It runs within a fixed step budget and logs, on every assistant message, the
tool used, the sources, token/char counts, and whether it abstained.
"""
from __future__ import annotations
import re

from . import config, db, llm, retrieval

# ---- intent cues ---------------------------------------------------------
_HUMAN_CUES = ("human", "talk to staff", "speak to staff", "real person",
               "a person", "customer service rep", "speak to someone",
               "talk to someone", "representative", "agent please",
               "can i talk to", "connect me", "real agent", "live agent")
_PRODUCT_CUES = ("price", "cost", "how much", "stock", "in stock", "available",
                 "availability", "do you have", "how many", "bags", "litres",
                 "liters", "kg", "quantity", "buy", "order", "sell")
# Strong cues mean the customer is clearly asking about a catalog item's price
# or availability; if we then find no match, we say so rather than fall back to
# documents (which could be a policy question phrased with "do you have").
_STRONG_PRODUCT_CUES = ("price", "cost", "how much", "stock", "in stock",
                        "available", "availability", "how many", "buy", "sell",
                        "order")
_PRODUCT_WORDS = {"price", "cost", "stock", "available", "availability", "buy",
                  "order", "how", "much", "many", "do", "you", "have", "the", "of",
                  "is", "are", "in", "a", "an", "and", "to", "i", "want", "need",
                  "can", "get", "me", "for", "what", "whats", "bags", "bag",
                  "litres", "liters", "kg", "please", "sell", "there", "any",
                  "your", "we", "it", "that", "this", "with", "about"}

# Words too generic to identify a specific product on their own.
_GENERIC_PRODUCT_WORDS = {"seed", "seeds", "fertilizer", "fertiliser", "fertilizers",
                          "pesticide", "pesticides", "tool", "tools", "irrigation",
                          "product", "products", "item", "items", "chemical", "chemicals"}


def _is_human_request(text: str) -> bool:
    t = text.lower()
    return any(cue in t for cue in _HUMAN_CUES)


def _is_product_query(text: str) -> bool:
    t = text.lower()
    return any(cue in t for cue in _PRODUCT_CUES)


def _product_terms(text: str) -> list[str]:
    """Extract likely product keywords (drop the question/filler words)."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in _PRODUCT_WORDS and len(w) > 2]


def _rank_products(tenant_id: str, terms: list[str]) -> list[dict]:
    """Rank catalog products by how well they match the *specific* query terms.

    Specific terms are matched against the product name (weighted) and category;
    generic words like "seed" or "fertilizer" alone cannot identify a product,
    so a query with no specific match returns nothing and the agent falls back
    to document retrieval instead of guessing.
    """
    specific = [t for t in terms if t not in _GENERIC_PRODUCT_WORDS]
    # Normalise to stemmed whole-word tokens so we match "DAP" but not the
    # "per" hidden inside "copper".
    specific_tokens = set(retrieval.tokenize(" ".join(specific)))
    if not specific_tokens:
        return []
    scored: list[tuple[int, dict]] = []
    for p in db.all_products(tenant_id):
        name_tokens = set(retrieval.tokenize(p["name"]))
        cat_tokens = set(retrieval.tokenize(p["category"]))
        score = 0
        for t in specific_tokens:
            if t in name_tokens:
                score += 2
            elif t in cat_tokens:
                score += 1
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: (-x[0], -x[1]["stock"]))
    return [p for _, p in scored]


def _handoff(tenant_id: str, conversation_id: int, reason: str, message: str,
             extra_meta: dict | None = None) -> dict:
    db.set_conversation_status(tenant_id, conversation_id, "waiting_staff")
    db.create_handoff(tenant_id, conversation_id, reason)
    meta = {"handoff": True, "reason": reason, "tool": None, "abstained": True}
    if extra_meta:
        meta.update(extra_meta)
    return db.add_message(tenant_id, conversation_id, "assistant", message, meta)


def run_agent(tenant_id: str, conversation_id: int, user_text: str) -> dict:
    """Process one customer message and return the assistant's reply message."""
    # Persist the customer's message first (saved history).
    db.add_message(tenant_id, conversation_id, "customer", user_text)

    steps = 0

    # 1) Explicit human request -> hand off with context.
    if _is_human_request(user_text):
        return _handoff(
            tenant_id, conversation_id, "customer_requested_human",
            "Of course - I'm connecting you with a staff member. I've shared our "
            "full conversation so they have the context.",
        )

    # 2) Product / catalog question -> product-lookup tool.
    if _is_product_query(user_text):
        steps += 1
        terms = _product_terms(user_text)
        matches = _rank_products(tenant_id, terms)
        if matches:
            lines = []
            for p in matches[:3]:
                status = f"{p['stock']} {p['unit']} in stock" if p["stock"] > 0 else "out of stock"
                lines.append(f"- {p['name']} ({p['sku']}): ${p['price']:.2f} per {p['unit']}, {status}")
            answer = "Here's what I found in our catalog:\n" + "\n".join(lines)
            meta = {
                "tool": "product_lookup", "steps": steps, "abstained": False,
                "sources": [{"title": "Product catalog", "source": f"catalog:{m['sku']}",
                             "score": 1.0} for m in matches[:3]],
                "chars_in": len(user_text), "chars_out": len(answer),
            }
            return db.add_message(tenant_id, conversation_id, "assistant", answer, meta)
        # No catalog match. If they clearly asked about price/stock, say the
        # item isn't in this supplier's catalog and hand off; otherwise fall
        # through to document retrieval (the question may be policy-related).
        if any(cue in user_text.lower() for cue in _STRONG_PRODUCT_CUES):
            return _handoff(
                tenant_id, conversation_id, "product_not_found",
                "I couldn't find that item in this supplier's catalog. I'm "
                "connecting you with a staff member who can check for you.",
                extra_meta={"tool": "product_lookup", "steps": steps},
            )

    # 3) Document-grounded answer (RAG) with abstention.
    steps += 1
    sources = retrieval.search(tenant_id, user_text)
    top_score = sources[0]["score"] if sources else 0.0

    # Coverage gate: a confident answer needs the retrieved evidence to share
    # at least two meaningful terms with the question. This stops a single
    # incidental word (e.g. "next") from producing a false, unsupported answer.
    q_terms = set(retrieval.tokenize(user_text))
    evidence_terms: set[str] = set()
    for s in sources:
        evidence_terms |= set(retrieval.tokenize(s["text"]))
    overlap = len(q_terms & evidence_terms)

    # Abstain when there is no evidence, the best match is weak, or the match
    # rests on a single term that is not also strongly similar. A strong single
    # term match (e.g. "drip") is allowed through.
    weak = (not sources
            or top_score < config.ABSTAIN_THRESHOLD
            or overlap == 0
            or (overlap < 2 and top_score < config.STRONG_SINGLE_TERM_SCORE))
    if weak:
        return _handoff(
            tenant_id, conversation_id, "insufficient_evidence",
            "I don't have approved information to answer that confidently, so I'm "
            "handing you to a staff member with your question and what I checked.",
            extra_meta={"tool": "doc_retrieval", "steps": steps,
                        "top_score": round(top_score, 4),
                        "sources": sources},
        )

    result = llm.grounded_answer(user_text, sources)
    if result["insufficient"]:
        return _handoff(
            tenant_id, conversation_id, "model_abstained",
            "I couldn't find a supported answer in our documents, so I'm bringing "
            "in a staff member who can help.",
            extra_meta={"tool": "doc_retrieval", "steps": steps, "sources": sources},
        )

    meta = {
        "tool": "doc_retrieval", "provider": result["provider"], "steps": steps,
        "abstained": False, "sources": sources,
        "chars_in": len(user_text), "chars_out": len(result["text"]),
    }
    return db.add_message(tenant_id, conversation_id, "assistant", result["text"], meta)
