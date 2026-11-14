"""AgriConnect AI - Update #1 demo slice.

A single, integrated FastAPI application that demonstrates:
  1. Web chat with saved history
  2. Grounded answers via retrieval over approved documents (with citations + abstention)
  3. A product-lookup tool over a simulated catalog
  4. Staff inbox + takeover (handoff carries full context)
  5. Multi-tenant isolation enforced at the API boundary

It runs fully offline (local TF-IDF retrieval + extractive answers) and
automatically uses a real LLM when an OPENAI_API_KEY is provided.
"""

__version__ = "0.1.0"
