from __future__ import annotations

import asyncio
import json
import re
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    name: str
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] | None = None
    cwd: str | None = None
    description: str | None = None
    enabled: bool = True
    tool_prefix: str | None = None


class MCPToolDescriptor(BaseModel):
    alias: str
    name: str
    server: str
    description: str | None = None
    title: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)

    def as_catalog_entry(self) -> str:
        summary = self.description or self.title or "No description."
        return f"{self.alias}: {summary} (server={self.server}, source={self.name})"

    def as_ollama_tool(self) -> dict[str, Any]:
        parameters = dict(self.input_schema or {})
        if "type" not in parameters:
            parameters["type"] = "object"
        parameters.setdefault("properties", {})
        return {
            "type": "function",
            "function": {
                "name": self.alias,
                "description": self.description or self.title or self.name,
                "parameters": parameters,
            },
        }


class ToolExecutionRecord(BaseModel):
    alias: str
    tool_name: str
    server: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    content: str
    structured_content: dict[str, Any] | None = None
    is_error: bool = False

    def as_ollama_message(self) -> dict[str, Any]:
        return {
            "role": "tool",
            "tool_name": self.alias,
            "content": self.model_dump_json(indent=2),
        }


class _MCPAttachment:
    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self._stack = AsyncExitStack()
        self._session: ClientSession | None = None
        self.tools: dict[str, MCPToolDescriptor] = {}

    async def start(self, *, used_aliases: set[str]) -> None:
        params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            env=self.config.env,
            cwd=self.config.cwd,
        )
        read_stream, write_stream = await self._stack.enter_async_context(stdio_client(params))
        session = ClientSession(read_stream, write_stream)
        self._session = await self._stack.enter_async_context(session)
        await self._session.initialize()
        await self.refresh_tools(used_aliases=used_aliases)

    async def close(self) -> None:
        await self._stack.aclose()

    async def refresh_tools(self, *, used_aliases: set[str]) -> None:
        if self._session is None:
            return

        listed = await self._session.list_tools()
        prefix = _slugify(self.config.tool_prefix or self.config.name)
        refreshed: dict[str, MCPToolDescriptor] = {}
        for tool in listed.tools:
            alias = _ensure_unique_alias(f"{prefix}__{_slugify(tool.name)}", used_aliases)
            used_aliases.add(alias)
            refreshed[alias] = MCPToolDescriptor(
                alias=alias,
                name=tool.name,
                server=self.config.name,
                description=tool.description,
                title=getattr(tool, "title", None),
                input_schema=dict(tool.inputSchema or {}),
            )
        self.tools = refreshed

    async def call_tool(self, descriptor: MCPToolDescriptor, arguments: dict[str, Any]) -> ToolExecutionRecord:
        if self._session is None:
            raise RuntimeError(f"MCP server {self.config.name} is not connected.")

        result = await self._session.call_tool(descriptor.name, arguments=arguments)
        content = _flatten_tool_content(result.content)
        structured_content = getattr(result, "structuredContent", None)
        if structured_content is not None and not isinstance(structured_content, dict):
            structured_content = {"value": structured_content}
        return ToolExecutionRecord(
            alias=descriptor.alias,
            tool_name=descriptor.name,
            server=self.config.name,
            arguments=arguments,
            content=content,
            structured_content=structured_content,
            is_error=bool(result.isError),
        )


class MCPToolRegistry:
    def __init__(self, configs: list[MCPServerConfig] | None = None, *, allow_partial: bool = True) -> None:
        self._configs = [config for config in (configs or []) if config.enabled]
        self._allow_partial = allow_partial
        self._attachments = [_MCPAttachment(config) for config in self._configs]
        self._tools: dict[str, tuple[_MCPAttachment, MCPToolDescriptor]] = {}
        self.startup_warnings: list[str] = []
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "MCPToolRegistry":
        await self.start()
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any) -> None:
        await self.close()

    async def start(self) -> None:
        used_aliases: set[str] = set()
        results = await asyncio.gather(
            *(attachment.start(used_aliases=used_aliases) for attachment in self._attachments),
            return_exceptions=True,
        )

        self._tools.clear()
        failures: list[Exception] = []
        for attachment, result in zip(self._attachments, results, strict=True):
            if isinstance(result, Exception):
                failures.append(result)
                self.startup_warnings.append(f"Failed to attach MCP server {attachment.config.name}: {result}")
                continue
            for alias, descriptor in attachment.tools.items():
                self._tools[alias] = (attachment, descriptor)

        if failures and not self._allow_partial:
            raise RuntimeError(f"Unable to initialize all MCP servers: {failures[0]}")

    async def close(self) -> None:
        await asyncio.gather(*(attachment.close() for attachment in self._attachments), return_exceptions=True)

    def render_catalog(self) -> list[str]:
        return [descriptor.as_catalog_entry() for _, descriptor in self._tools.values()]

    def ollama_tools(self) -> list[dict[str, Any]]:
        return [descriptor.as_ollama_tool() for _, descriptor in self._tools.values()]

    async def call_tool(self, alias: str, arguments: dict[str, Any] | None = None) -> ToolExecutionRecord:
        try:
            attachment, descriptor = self._tools[alias]
        except KeyError as exc:
            raise KeyError(f"Unknown MCP tool alias: {alias}") from exc

        async with self._lock:
            return await attachment.call_tool(descriptor, arguments or {})


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip().lower()).strip("_")
    return normalized or "tool"


def _ensure_unique_alias(candidate: str, used_aliases: set[str]) -> str:
    if candidate not in used_aliases:
        return candidate

    index = 2
    while f"{candidate}_{index}" in used_aliases:
        index += 1
    return f"{candidate}_{index}"


def _flatten_tool_content(content: list[Any]) -> str:
    fragments: list[str] = []
    for item in content:
        item_type = getattr(item, "type", None)
        if item_type == "text":
            fragments.append(item.text)
            continue
        if hasattr(item, "model_dump_json"):
            fragments.append(item.model_dump_json(indent=2))
            continue
        fragments.append(json.dumps(item, ensure_ascii=True, default=str))
    return "\n".join(fragment for fragment in fragments if fragment).strip()
