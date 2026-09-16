"""Chat client for the Snapdragon X Elite: local Qwen 3 (GenieX) + the Uno Q's MCP tools.

GenieX serves an OpenAI-compatible API at http://127.0.0.1:18181/v1. The MCP server runs on
the Uno Q's Linux side and is reached over adb stdio, so no port forwarding is needed.

    geniex serve                      # in another terminal
    python -m x_elite.client

Then ask e.g. "check samples/authorized.json" or "turn the light red".
"""
import asyncio
import json
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

ADB = os.environ.get(
    "ADB", os.path.expandvars(r"%LOCALAPPDATA%\Arduino15\packages\arduino\tools\adb\32.0.0\adb.exe")
)
REMOTE = "cd /home/arduino/rpc && MSGPACK_PUREPYTHON=1 python3 mcp_server.py"
BASE_URL = os.environ.get("GENIEX_URL", "http://127.0.0.1:18181/v1")
MODEL = os.environ.get("GENIEX_MODEL", "qualcomm/Qwen3-4B-Instruct-2507")

SYSTEM = (
    "You control an Arduino Uno Q that shows whether someone is authorized on a Modulino Pixels "
    "LED strip. Use the tools to check files and set the light. Files live next to the server, "
    "e.g. samples/authorized.json and samples/unauthorized.json. Keep answers to one sentence."
)


async def chat():
    server = StdioServerParameters(command=ADB, args=["shell", REMOTE])
    async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = (await session.list_tools()).tools
        schema = [
            {
                "type": "function",
                "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema},
            }
            for t in tools
        ]
        print(f"connected to Uno Q, tools: {', '.join(t.name for t in tools)}")

        llm = OpenAI(base_url=BASE_URL, api_key="not-needed")
        messages = [{"role": "system", "content": SYSTEM}]

        while True:
            try:
                prompt = input("\nyou> ").strip()
            except (EOFError, KeyboardInterrupt):
                return
            if not prompt or prompt in {"quit", "exit"}:
                return

            messages.append({"role": "user", "content": prompt})
            # Loop so the model can chain calls (check a file, then react to the result).
            while True:
                reply = llm.chat.completions.create(model=MODEL, messages=messages, tools=schema).choices[0].message
                messages.append(reply.model_dump(exclude_none=True))
                if not reply.tool_calls:
                    print(f"qwen> {reply.content}")
                    break

                for call in reply.tool_calls:
                    args = json.loads(call.function.arguments or "{}")
                    print(f"  [tool] {call.function.name}({args})")
                    result = await session.call_tool(call.function.name, args)
                    text = "\n".join(c.text for c in result.content if c.type == "text")
                    print(f"  [board] {text}")
                    messages.append({"role": "tool", "tool_call_id": call.id, "content": text})


if __name__ == "__main__":
    asyncio.run(chat())
