"""Provider adapters: one call to one model, through LangChain chat models.

LangChain gives the same interface for Gemini and OpenAI, including tool
calling (`bind_tools`) and structured output (`with_structured_output`).
Everything around the call (cache, limits, retries, fallback, cost) is in
the gateway, so this layer stays a thin translation.
"""

from dataclasses import dataclass, field
from typing import Protocol

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from investigator.config import ModelSpec, Secrets
from investigator.llm.errors import LLMBadOutput


@dataclass
class RawResponse:
    text: str
    parsed: dict | None = None  # structured output, as plain JSON-able data
    tool_calls: list[dict] = field(default_factory=list)  # [{"name", "args", "id"}]
    input_tokens: int = 0
    output_tokens: int = 0


class ChatBackend(Protocol):
    def invoke(
        self, messages: list[dict], schema: type[BaseModel] | None, tools: list | None
    ) -> RawResponse: ...


def to_langchain(messages: list[dict]) -> list:
    """Plain dicts -> LangChain messages. Roles: system, user, assistant, tool."""
    converted = []
    for m in messages:
        role, content = m["role"], m.get("content", "")
        if role == "system":
            converted.append(SystemMessage(content))
        elif role == "user":
            converted.append(HumanMessage(content))
        elif role == "assistant":
            converted.append(AIMessage(content, tool_calls=m.get("tool_calls", [])))
        elif role == "tool":
            converted.append(ToolMessage(content, tool_call_id=m["tool_call_id"]))
        else:
            raise ValueError(f"Unknown message role: {role}")
    return converted


class LangChainBackend:
    def __init__(self, model: BaseChatModel):
        self.model = model

    def invoke(self, messages, schema=None, tools=None) -> RawResponse:
        lc_messages = to_langchain(messages)
        parsed = None
        if schema is not None:
            out = self.model.with_structured_output(schema, include_raw=True).invoke(lc_messages)
            if out.get("parsing_error") or out.get("parsed") is None:
                raise LLMBadOutput(
                    f"Output did not match {schema.__name__}: {out.get('parsing_error')}"
                )
            raw, parsed = out["raw"], out["parsed"].model_dump()
        elif tools:
            raw = self.model.bind_tools(tools).invoke(lc_messages)
        else:
            raw = self.model.invoke(lc_messages)

        usage = raw.usage_metadata or {}
        return RawResponse(
            text=raw.text if isinstance(raw.text, str) else str(raw.content),
            parsed=parsed,
            tool_calls=[
                {"name": t["name"], "args": t["args"], "id": t["id"]} for t in raw.tool_calls
            ],
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )


def make_backend(spec: ModelSpec, secrets: Secrets, timeout_s: float) -> LangChainBackend:
    """max_retries=0: the gateway's own retry policy is the only one."""
    if spec.provider == "gemini":
        kwargs = {"temperature": spec.temperature} if spec.temperature is not None else {}
        model = ChatGoogleGenerativeAI(
            model=spec.name,
            google_api_key=secrets.gemini_api_key.get_secret_value(),
            max_retries=0,
            timeout=timeout_s,
            **kwargs,
        )
    else:
        kwargs = {}
        if spec.temperature is not None:
            kwargs["temperature"] = spec.temperature
        if spec.reasoning_effort:
            kwargs["reasoning_effort"] = spec.reasoning_effort
        model = ChatOpenAI(
            model=spec.name,
            api_key=secrets.openai_api_key.get_secret_value(),
            max_retries=0,
            timeout=timeout_s,
            **kwargs,
        )
    return LangChainBackend(model)
