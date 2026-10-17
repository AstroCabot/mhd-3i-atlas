#!/usr/bin/env python3
"""Export the three identified research conversations without changing their logs.

The session allowlist deliberately excludes the app-building conversation and all
unrelated account history. Sources are opened read-only; generated text lives in
the application directory. Reasoning is exported only when plaintext was actually
recorded. Encrypted payloads/signatures are counted, never decoded or invented.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import re
import sqlite3
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
RESEARCH = APP.parent / "mhd_llm"
HOME = Path.home()
CODEX_ID = "01a146ba-a9cd-76b3-aed6-4038d965cff7"
CLAUDE_ID = "c4794a53-4881-4aa9-8b9b-7c033457fa8b"
ARGON_ID = "b3d3df79-0b74-4e57-8d1f-8f7268882191"
OUT = APP / "public/data"
MAX_TEXT = 60000
CHUNK_BYTES = 240000
CHUNK_MESSAGES = 40
REDACTIONS = collections.Counter()

DISCLOSURE = (
    "Read-only snapshot of the identified research sessions and their recorded "
    "subagents. Dialogue, tool text, and readable recorded reasoning are preserved "
    "apart from credential redaction and reversible pagination. Encrypted reasoning "
    "and encrypted messages are unavailable; no hidden reasoning is reconstructed. "
    "System/developer instructions, signatures, API request bodies, images, and "
    "unrelated sessions are excluded. Timestamps are recorded UTC where available. "
    "An unavailable entry is an editorial status label, not a quotation."
)


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def lines(path):
    with path.open(encoding="utf-8", errors="replace") as stream:
        for number, line in enumerate(stream, 1):
            try:
                yield number, json.loads(line)
            except json.JSONDecodeError:
                # An active session may have a final incomplete record.
                continue


def redact(text):
    if not isinstance(text, str):
        text = json.dumps(text, ensure_ascii=False, indent=2)
    patterns = [
        (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "[REDACTED PRIVATE KEY]"),
        (r"\b(?:sk-(?:proj-|ant-)?[A-Za-z0-9_\-]{16,}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AIza[A-Za-z0-9_\-]{30,})\b", "[REDACTED CREDENTIAL]"),
        (r"(?i)(\b(?:authorization|proxy-authorization)\s*[:=]\s*[\"']?(?:Bearer|Basic)\s+)[^\s\"'\\]+", r"\1[REDACTED]"),
        (r"(?i)(\b[A-Z_]*(?:API_KEY|ACCESS_TOKEN|AUTH_TOKEN|REFRESH_TOKEN|CLIENT_SECRET|PASSWORD|SECRET_ACCESS_KEY|SESSION_TOKEN)\b[\"']?\s*[:=]\s*[\"']?)([^\s\"'\n,;}]+)", r"\1[REDACTED]"),
        (r"(?i)(\b(?:GH_TOKEN|GITHUB_TOKEN|HF_TOKEN|HUGGINGFACE_TOKEN|NPM_TOKEN|PYPI_TOKEN|NASA_TOKEN|EARTHDATA_TOKEN|BEARER_TOKEN|AWS_SECURITY_TOKEN)\b[\"']?\s*[:=]\s*[\"']?)([^\s\"'\n,;}]+)", r"\1[REDACTED]"),
        (r"(?im)(\b(?:cookie|set-cookie)\s*:\s*)[^\r\n]+", r"\1[REDACTED]"),
        (r"(?i)(https?://)[^\s/:@]+:[^\s/@]+@", r"\1[REDACTED CREDENTIALS]@"),
        (r"(?i)([?&](?:access_token|api_key|token|key|signature|x-amz-signature|sig)=)[^&\s\"'<>]+", r"\1[REDACTED]"),
        (r"\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}\b", "[REDACTED AUTH TOKEN]"),
        (r"\bgAAAAA[A-Za-z0-9_=\-]{40,}", "[encrypted payload unavailable]"),
    ]
    for pattern, replacement in patterns:
        text, count = re.subn(pattern, replacement, text)
        if count:
            REDACTIONS["encrypted_payload" if "gAAAAA" in pattern else "credential"] += count
    return text


def content_text(content):
    """Extract text blocks; retain a clear marker for unavailable encrypted text."""
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") in ("text", "input_text", "output_text", "summary_text"):
                    parts.append(block.get("text", ""))
                elif block.get("type") in ("encrypted_content", "redacted_thinking"):
                    parts.append("[encrypted payload unavailable]")
        return "\n".join(parts)
    return json.dumps(content, ensure_ascii=False, indent=2)


def directed(text):
    """Conservative address detection; mentions alone do not imply an exchange."""
    found = set()
    patterns = [
        r"(?im)^\s*(?:to|for|cc|dear|attention|reply\s+to|response\s+to)\s*[:\-]?\s*([^\n]{0,100})",
        r"(?im)^\s*\*{0,2}(?:codex|claude|argon)(?:\*{0,2})\s*[:,—-][^\n]{0,80}",
        r"(?im)^\s*#+\s*(?:to|for|reply\s+to|response\s+to)\s+([^\n]+)",
        r"(?i)@(?:codex|claude|argon)\b",
        r"(?i)\b(?:codex|claude|argon)\s*(?:→|->|to)\s*(?:codex|claude|argon)\b",
        r"(?im)\b(?:reply\s*to|response\s*to|question\s+for|request\s+for|etiquette\s+for|thanks\s+to)\s*[^\n]{0,180}",
        r"(?im)\b(?:to|for)\s+`?(?:codex|claude|argon)\b[^\n]{0,120}",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            for agent in ("argon", "codex", "claude"):
                if re.search(rf"\b{agent}\b", match.group(0), re.I):
                    found.add(agent)
    return sorted(found)


def base_session(session_id, agent, name, provider, parent=None):
    return {
        "id": session_id, "session_hash": session_id, "agent": agent,
        "name": name, "provider": provider, "parent_id": parent,
        "model": None, "reasoning_level": None, "started_at": None,
        "ended_at": None, "subagent_count": 0, "tokens": None,
        "message_count": 0, "availability": {}, "source": None,
        "identification": "", "chunks": [],
    }


def message(session, number, timestamp, role, kind, text, **extra):
    clean = redact(text)
    if not clean:
        return None
    return {
        "id": f"{session}-{number}-{extra.pop('block', 0)}", "timestamp": timestamp,
        "role": role, "kind": kind, "text": clean, "source_line": number,
        "directed_to": directed(clean) if kind not in ("tool_result", "unavailable") else [],
        **extra,
    }


def parse_codex(path, parent=None):
    records = list(lines(path))
    meta = next(d["payload"] for _, d in records if d.get("type") == "session_meta")
    sid = meta["id"]
    session = base_session(sid, "codex", "Codex" if not parent else "Codex · " + meta.get("agent_path", sid).split("/")[-1], "OpenAI", parent)
    session["source"] = "~/.codex/sessions/" + str(path.relative_to(HOME / ".codex/sessions"))
    session["started_at"] = meta.get("timestamp")
    session["cli_version"] = meta.get("cli_version")
    session["agent_path"] = meta.get("agent_path", "/root")
    session["identification"] = (
        "mhd_codex tmux pane runs codex in the X3I project; this rollout records the exact mhd_llm/codex prompt and three matching child thread IDs."
        if not parent else "session_meta.parent_thread_id points to the identified Codex research session. Inherited parent-context entries are excluded."
    )
    messages, encrypted, readable = [], 0, 0
    spawned = set()
    start = dt.datetime.fromisoformat(session["started_at"].replace("Z", "+00:00")).timestamp()
    for number, record in records:
        timestamp = record.get("timestamp")
        session["ended_at"] = timestamp or session["ended_at"]
        payload = record.get("payload", {})
        if record.get("type") == "turn_context":
            session["model"] = payload.get("model") or session["model"]
            session["reasoning_level"] = payload.get("effort") or session["reasoning_level"]
        if record.get("type") == "event_msg" and payload.get("type") == "token_count":
            usage = payload.get("info", {}).get("total_token_usage")
            if usage:
                session["tokens"] = {**usage, "scope": "this session, reported cumulative token usage", "method": "last event_msg/token_count.info.total_token_usage; cached input is included in input_tokens"}
        if record.get("type") != "response_item":
            continue
        typ = payload.get("type")
        created = payload.get("internal_chat_message_metadata_passthrough", {}).get("create_time")
        if parent and created and created < start:
            continue
        common = {"channel": payload.get("channel")}
        entry = None
        if typ == "message" and payload.get("role") in ("user", "assistant"):
            text = content_text(payload.get("content"))
            # Environment wrappers are metadata, not the research dialogue.
            if text.lstrip().startswith("<environment_context>"):
                continue
            entry = message(sid, number, timestamp, payload["role"], payload["role"], text, **common)
        elif typ in ("custom_tool_call", "function_call"):
            name = payload.get("name", "tool")
            tool_input = payload.get("input", payload.get("arguments", ""))
            entry = message(sid, number, timestamp, "assistant", "tool_call", tool_input, tool_name=name, call_id=payload.get("call_id"), **common)
            if name == "spawn_agent":
                try:
                    spawned.add(json.loads(tool_input).get("task_name"))
                except (ValueError, TypeError):
                    pass
        elif typ in ("custom_tool_call_output", "function_call_output"):
            entry = message(sid, number, timestamp, "tool", "tool_result", content_text(payload.get("output")), call_id=payload.get("call_id"))
        elif typ == "agent_message":
            entry = message(sid, number, timestamp, payload.get("author", "agent"), "coordination", content_text(payload.get("content")), recipient=payload.get("recipient"), availability="partly_encrypted" if any(isinstance(b, dict) and b.get("type") == "encrypted_content" for b in payload.get("content", [])) else "recorded")
        elif typ == "reasoning":
            text = content_text(payload.get("summary", []))
            if payload.get("content"):
                text += content_text(payload["content"])
            if text.strip():
                readable += 1
                entry = message(sid, number, timestamp, "assistant", "recorded_reasoning", text, availability="recorded")
            elif payload.get("encrypted_content"):
                encrypted += 1
                entry = message(sid, number, timestamp, "assistant", "unavailable", "Reasoning is encrypted in the local session log; plaintext is unavailable.", availability="encrypted", original_kind="recorded_reasoning")
        if entry:
            messages.append(entry)
    session["subagent_count"] = len(spawned)
    session["availability"] = {"readable_reasoning_records": readable, "unavailable_reasoning_records": encrypted, "notes": "Encrypted content is not decrypted. Tool calls and responses are the recorded text."}
    return session, messages


def parse_claude(path, parent=None):
    sid = path.stem if not parent else path.stem.removeprefix("agent-")
    session = base_session(sid, "claude", "Claude" if not parent else "Claude · " + sid, "Anthropic", parent)
    session["source"] = "~/.claude/projects/" + str(path.relative_to(HOME / ".claude/projects"))
    session["identification"] = (
        "The mhd_claude process holds an open descriptor under this exact session's tasks directory; the JSONL records the mhd_llm/claude research prompt."
        if not parent else "Session-specific subagents directory and matching sessionId associate this sidechain with the identified Claude root."
    )
    messages, usage_by_id, seen = [], {}, set()
    agent_calls, launched_agents = {}, {}
    readable = unavailable = 0
    for number, record in lines(path):
        timestamp = record.get("timestamp")
        if timestamp:
            session["started_at"] = min(session["started_at"], timestamp) if session["started_at"] else timestamp
            session["ended_at"] = max(session["ended_at"], timestamp) if session["ended_at"] else timestamp
        session["cli_version"] = record.get("version") or session.get("cli_version")
        if record.get("type") == "api-request":
            params = record.get("params", {})
            session["reasoning_level"] = params.get("output_config", {}).get("effort") or session["reasoning_level"]
            session["model"] = params.get("model") or session["model"]
        if record.get("type") not in ("user", "assistant"):
            continue
        # Some Claude logs repeat events after resumptions. UUIDs are stable.
        uuid = record.get("uuid")
        if uuid and uuid in seen:
            continue
        if uuid:
            seen.add(uuid)
        msg = record.get("message", {})
        if record.get("type") == "assistant":
            session["model"] = msg.get("model") or session["model"]
            if msg.get("id") and msg.get("usage"):
                usage_by_id[msg["id"]] = msg["usage"]
        content = msg.get("content", "")
        if isinstance(content, str):
            entry = message(sid, number, timestamp, msg.get("role", record["type"]), record["type"], content)
            if entry:
                messages.append(entry)
            if "Set effort level to " in content:
                match = re.search(r"Set effort level to (\w+)", content)
                if match:
                    session["reasoning_level"] = match[1]
            continue
        for index, block in enumerate(content):
            if not isinstance(block, dict):
                continue
            typ = block.get("type")
            extra = {"block": index}
            entry = None
            if typ == "text":
                entry = message(sid, number, timestamp, msg.get("role", "assistant"), record["type"], block.get("text", ""), **extra)
            elif typ in ("thinking", "redacted_thinking"):
                text = block.get("thinking", "")
                if text:
                    readable += 1
                    entry = message(sid, number, timestamp, "assistant", "recorded_reasoning", text, availability="recorded", **extra)
                else:
                    unavailable += 1
                    entry = message(sid, number, timestamp, "assistant", "unavailable", "The local log contains an empty or redacted thinking block; plaintext is unavailable.", availability="empty_or_redacted", original_kind="recorded_reasoning", **extra)
            elif typ == "tool_use":
                entry = message(sid, number, timestamp, "assistant", "tool_call", block.get("input", {}), tool_name=block.get("name"), call_id=block.get("id"), **extra)
                if block.get("name") in ("Agent", "Task"):
                    agent_calls[block.get("id")] = block.get("input", {}).get("description")
            elif typ == "tool_result":
                entry = message(sid, number, timestamp, "tool", "tool_result", content_text(block.get("content")), call_id=block.get("tool_use_id"), **extra)
                if block.get("tool_use_id") in agent_calls:
                    for agent_id in re.findall(r"agentId[:= ]+([a-f0-9]{8,})", content_text(block.get("content"))):
                        launched_agents[agent_id] = agent_calls[block["tool_use_id"]]
            if entry:
                messages.append(entry)
    totals = collections.Counter()
    for usage in usage_by_id.values():
        for key in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens"):
            totals[key] += usage.get(key, 0) or 0
        totals["reasoning_output_tokens"] += usage.get("output_tokens_details", {}).get("thinking_tokens", 0) or 0
    input_total = totals["input_tokens"] + totals["cache_read_input_tokens"] + totals["cache_creation_input_tokens"]
    session["tokens"] = {
        "input_tokens": input_total, "uncached_input_tokens": totals["input_tokens"],
        "cached_input_tokens": totals["cache_read_input_tokens"], "cache_write_input_tokens": totals["cache_creation_input_tokens"],
        "output_tokens": totals["output_tokens"], "reasoning_output_tokens": totals["reasoning_output_tokens"],
        "total_tokens": input_total + totals["output_tokens"], "request_count": len(usage_by_id),
        "scope": "this session's recorded API responses",
        "method": "sum of the last recorded usage per unique message.id; input includes uncached, cache read, and cache creation; output includes thinking",
    }
    session["availability"] = {"readable_reasoning_records": readable, "unavailable_reasoning_records": unavailable, "notes": "Only nonempty recorded thinking text is shown. Signatures and request bodies are excluded."}
    session["launched_agents"] = launched_agents
    return session, messages


def parse_argon(path, parent=None, name=None):
    sid = path.parents[2].name
    session = base_session(sid, "argon", name or ("Argon" if not parent else "Argon · research"), "Google / Antigravity", parent)
    session["source"] = "~/.gemini/antigravity-cli/brain/" + str(path.relative_to(HOME / ".gemini/antigravity-cli/brain"))
    session["identification"] = (
        "mhd_argon runs agy; its stdout descriptor points to cli-20261016_233143.log. Antigravity history associates the exact mhd_llm/argon request and X3I working directory with this conversation hash."
        if not parent else "conversation_summaries.db explicitly records the identified Argon research session as parent_conversation_id."
    )
    messages = []
    totals = collections.Counter()
    readable = 0
    for number, record in lines(path):
        timestamp = record.get("created_at")
        session["started_at"] = session["started_at"] or timestamp
        session["ended_at"] = timestamp or session["ended_at"]
        typ = record.get("type")
        text = record.get("content", "")
        if typ == "USER_INPUT":
            model = re.search(r"Model Selection` from .*? to ([^.\n]+)\.", text)
            if model:
                session["model"] = model[1]
                level = re.search(r"\(([^)]+)\)", model[1])
                session["reasoning_level"] = level[1].lower() if level else None
            entry = message(sid, number, timestamp, "user", "user", text)
            if entry:
                messages.append(entry)
        elif typ == "PLANNER_RESPONSE":
            for key in ("input_tokens", "cache_read_tokens", "output_tokens"):
                totals[key] += record.get(key, 0) or 0
            if record.get("thinking"):
                readable += 1
                messages.append(message(sid, number, timestamp, "assistant", "recorded_reasoning", record["thinking"], availability="recorded"))
            if text:
                messages.append(message(sid, number, timestamp, "assistant", "assistant", text, block=1))
            for index, call in enumerate(record.get("tool_calls", [])):
                messages.append(message(sid, number, timestamp, "assistant", "tool_call", call.get("args", {}), tool_name=call.get("name"), block=index + 2))
        elif typ == "GENERIC":
            entry = message(sid, number, timestamp, "tool", "tool_result", text)
            if entry:
                messages.append(entry)
        elif typ == "SYSTEM_MESSAGE" and "[Message]" in text:
            # These are recorded inter-agent messages carried in a system envelope.
            sender = re.search(r"\bsender=([^\s]+)", text)
            entry = message(sid, number, timestamp, sender[1] if sender else "agent", "coordination", text)
            if entry:
                messages.append(entry)
        elif typ == "CHECKPOINT":
            entry = message(sid, number, timestamp, "system", "recorded_summary", text, availability="recorded_compaction_summary")
            if entry:
                messages.append(entry)
    session["tokens"] = {
        "input_tokens": totals["input_tokens"] + totals["cache_read_tokens"], "uncached_input_tokens": totals["input_tokens"], "cached_input_tokens": totals["cache_read_tokens"],
        "output_tokens": totals["output_tokens"], "reasoning_output_tokens": None,
        "total_tokens": totals["input_tokens"] + totals["cache_read_tokens"] + totals["output_tokens"],
        "scope": "recorded planner responses in this session",
        "method": "sum of transcript_full planner-response fields; normalized input adds recorded input_tokens and cache_read_tokens, and total adds output_tokens; thinking-token split is unavailable",
    }
    session["availability"] = {"readable_reasoning_records": readable, "unavailable_reasoning_records": 0, "notes": "Readable reasoning records are preserved in transcript_full.jsonl. Child model and reasoning settings are shown only where recorded."}
    return session, [m for m in messages if m]


def chunk_session(session, messages):
    """Split large text reversibly, and write bounded chunks plus a compact index."""
    normalized = []
    for item in messages:
        text = item["text"]
        if len(text) <= MAX_TEXT:
            normalized.append(item)
        else:
            parts = (len(text) + MAX_TEXT - 1) // MAX_TEXT
            for part in range(parts):
                normalized.append({**item, "id": f"{item['id']}-part{part + 1}", "original_id": item["id"], "part": part + 1, "parts": parts, "text": text[part * MAX_TEXT:(part + 1) * MAX_TEXT]})
    session["message_count"] = len(normalized)
    session["source_message_count"] = len(messages)
    session["kind_counts"] = dict(collections.Counter(m["kind"] for m in normalized))
    session["directed_message_count"] = sum(bool(m["directed_to"]) or m["kind"] == "coordination" for m in normalized)
    chunks, current, size = [], [], 0
    for item in normalized:
        item_size = len(json.dumps(item, ensure_ascii=False).encode("utf-8"))
        if current and (size + item_size > CHUNK_BYTES or len(current) >= CHUNK_MESSAGES):
            chunks.append(current)
            current, size = [], 0
        current.append(item)
        size += item_size
    if current:
        chunks.append(current)
    search = []
    for index, chunk in enumerate(chunks):
        relative = f"transcripts/{session['id']}/{index:04d}.json"
        write_json(OUT / relative, {"session_id": session["id"], "index": index, "messages": chunk})
        session["chunks"].append({"url": "/data/" + relative, "count": len(chunk), "start": chunk[0]["timestamp"], "end": chunk[-1]["timestamp"]})
        for item in chunk:
            terms = sorted(set(re.findall(r"[a-z][a-z0-9_./-]{2,40}", item["text"].lower())))
            search.append({"id": item["id"], "chunk": index, "timestamp": item["timestamp"], "role": item["role"], "kind": item["kind"], "text": item["text"][:1000], "terms": " ".join(terms), "directed_to": item["directed_to"]})
    search_relative = f"transcripts/{session['id']}/search.json"
    write_json(OUT / search_relative, {"session_id": session["id"], "search_note": "text is a verbatim excerpt; terms index all words in the complete entry. Use chunk to fetch the full entry. Term search is case-insensitive; phrase matches require reading the corresponding chunk.", "messages": search})
    session["search_url"] = "/data/" + search_relative
    return session


def parse_note_time(filename):
    match = re.search(r"(20\d{6})T(\d{4}(?:\d{2})?)Z", filename)
    if not match:
        return None, None
    date, time = match.groups()
    timestamp = dt.datetime.strptime(date + time, "%Y%m%d%H%M%S" if len(time) == 6 else "%Y%m%d%H%M").replace(tzinfo=dt.timezone.utc)
    return timestamp.isoformat().replace("+00:00", "Z"), "second" if len(time) == 6 else "minute"


def build_notes():
    notes = []
    for path in sorted((RESEARCH / "shared_notes").iterdir()):
        if not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        text = redact(raw)
        timestamp, precision = parse_note_time(path.name)
        author = next((agent for agent in ("argon", "codex", "claude") if agent in path.name.lower()), "unknown")
        title = next((line.strip().lstrip("# ") for line in text.splitlines() if line.strip()), path.name)
        addressed = directed(text)
        # An agent's own name in an address/signature is not a recipient.
        addressed = [agent for agent in addressed if agent != author]
        exchange_lines = [line for line in text.splitlines() if directed(line)]
        notes.append({
            "id": path.stem, "filename": path.name, "author": author,
            "timestamp": timestamp, "timestamp_precision": precision,
            "timestamp_source": "filename" if timestamp else None,
            "title": title[:200], "text": text, "directed_to": addressed,
            "exchange_excerpt": "\n".join(exchange_lines)[:1200] if addressed else None,
            "source": "mhd_llm/shared_notes/" + path.name,
            "source_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        })
    notes.sort(key=lambda n: (n["timestamp"] or "", n["filename"]))
    for note in notes:
        note["references"] = [other["id"] for other in notes if other["id"] != note["id"] and (other["filename"] in note["text"] or other["id"] in note["text"])]
    write_json(OUT / "shared-notes.json", {"generated_at": utc_now(), "disclosure": "Full readable shared_notes files, with credential redaction where necessary. Filename timestamps preserve the recorded precision; they are not filesystem modification times. Directed recipients are conservatively detected from address lines.", "notes": notes})
    return {"url": "/data/shared-notes.json", "count": len(notes), "directed_count": sum(bool(n["directed_to"]) for n in notes)}


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.output.resolve()
    all_sessions = []
    codex_paths = list((HOME / ".codex/sessions").rglob("*.jsonl"))
    codex_selected = []
    for path in codex_paths:
        try:
            _, first = next(lines(path))
        except StopIteration:
            continue
        meta = first.get("payload", {})
        if first.get("type") == "session_meta" and (meta.get("id") == CODEX_ID or meta.get("parent_thread_id") == CODEX_ID):
            codex_selected.append((path, meta))
    for path, meta in sorted(codex_selected, key=lambda item: item[1].get("timestamp", "")):
        parent = CODEX_ID if meta.get("id") != CODEX_ID else None
        session, messages = parse_codex(path, parent)
        all_sessions.append(chunk_session(session, messages))
    claude_root = HOME / ".claude/projects/-mnt-c-Users-cabot-OneDrive-Documents-Research-Cambridge-X3I" / (CLAUDE_ID + ".jsonl")
    for path in [claude_root, *sorted(claude_root.with_suffix("").glob("subagents/*.jsonl"))]:
        session, messages = parse_claude(path, CLAUDE_ID if path != claude_root else None)
        all_sessions.append(chunk_session(session, messages))
    agy_root = HOME / ".gemini/antigravity-cli"
    con = sqlite3.connect("file:" + str(agy_root / "conversation_summaries.db") + "?mode=ro", uri=True)
    rows = con.execute("SELECT conversation_id,parent_conversation_id,agent_name FROM conversation_summaries WHERE conversation_id = ? OR parent_conversation_id = ?", (ARGON_ID, ARGON_ID)).fetchall()
    con.close()
    for sid, parent, agent_name in sorted(rows, key=lambda row: bool(row[1])):
        path = agy_root / "brain" / sid / ".system_generated/logs/transcript_full.jsonl"
        session, messages = parse_argon(path, parent or None, "Argon · " + agent_name if parent else "Argon")
        all_sessions.append(chunk_session(session, messages))
    for session in all_sessions:
        for child_id, description in session.get("launched_agents", {}).items():
            child = next((s for s in all_sessions if s["id"] == child_id), None)
            if child:
                child["parent_id"] = session["id"]
                child["task_description"] = description
                child["name"] = "Claude · " + description if description else child["name"]
                child["identification"] += " Immediate parent confirmed by the Agent tool result's recorded agentId."
    for session in all_sessions:
        children = [s for s in all_sessions if s["parent_id"] == session["id"]]
        descendants = {s["id"] for s in children}
        while True:
            expanded = descendants | {s["id"] for s in all_sessions if s["parent_id"] in descendants}
            if expanded == descendants:
                break
            descendants = expanded
        root = session
        while root["parent_id"]:
            root = next(s for s in all_sessions if s["id"] == root["parent_id"])
        session["root_id"] = root["id"]
        session["direct_subagent_count"] = len(children)
        session["subagent_count"] = len(descendants)
        session["subagent_ids"] = sorted(descendants)
    all_sessions.sort(key=lambda s: (("argon", "codex", "claude").index(s["agent"]), bool(s["parent_id"]), s["started_at"] or ""))
    notes = build_notes()
    result = {
        "schema_version": 1, "generated_at": utc_now(), "disclosure": DISCLOSURE,
        "sessions": all_sessions, "notes": notes,
        "stats": {"main_sessions": sum(not s["parent_id"] for s in all_sessions), "subagent_sessions": sum(bool(s["parent_id"]) for s in all_sessions), "messages": sum(s["message_count"] for s in all_sessions), "notes": notes["count"], "redactions": dict(REDACTIONS)},
        "token_comparability": "Token figures describe recorded API traffic, including repeated cached context. They are not unique words, monetary costs, GPU time, or measured scientific compute. Provider accounting and logging scopes differ; no billing costs are inferred.",
    }
    write_json(OUT / "transcripts.json", result)
    print(json.dumps({"output": str(OUT / "transcripts.json"), "stats": result["stats"], "sessions": [{k: s[k] for k in ("agent", "name", "id", "parent_id", "model", "reasoning_level", "message_count", "subagent_count")} for s in all_sessions]}, indent=2))


if __name__ == "__main__":
    main()
