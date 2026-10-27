"""Prompts for the agent's steps. The final answer reuses rag.prompts.ANSWER_SYSTEM."""

AGENT_PROMPT_VERSION = "agent-v1"

PLAN_SYSTEM = """Break the user's question into the smallest steps needed to answer it.

- single: one fact about one thing -> one sub-question.
- bridge: the question describes something without naming it ("the director of the film
  that...") -> first find that thing, then ask about it.
- comparison: the same property of two or more things -> one sub-question per thing.
Write 1-3 short sub-questions. Do not answer them."""

RETRIEVE_SYSTEM = """You plan searches over a document collection.
Call the search_documents tool once for each search that is needed now, at most {max_queries}.
Prefer exact names. When earlier results already name the entity you need (a person, film,
company), search for that name and the fact wanted, not for words from the question.
Do not answer the question."""

GRADE_SYSTEM = """Decide whether the sources below are enough to answer every sub-question.
Use only what the sources say. If something is missing, say what, and suggest up to
{max_queries} follow-up searches that use names mentioned in the sources.

Sources:
{sources}"""

EXTRACT_SYSTEM = """List the facts in the sources that bear on the question, one per statement,
as (subject, attribute, value, source label). Use the same short subject name and the
same attribute words whenever two sources talk about the same property, so they can be
compared. Copy values as the source states them. Mark single_valued correctly: a person has
one birth date, but can act in many films. Do not add facts that are not in the sources.

Sources:
{sources}"""

CONFLICT_NOTE = """

A claim check found these disagreements between sources:
{conflicts}
If they matter for the answer, use status "contradictory" and give both versions,
each with its sources."""
