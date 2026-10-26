r"""
Real-time Subagent, Task & Conversation Runtime + Token Telemetry Monitor.
Writes and updates `C:\Users\Felipe\Documents\coding\montreal\TELEMETRY_STATUS.md`
every 60 seconds when run with `--watch` (or once when run without arguments).
"""
import os
import sys
import time
import json
import argparse
from datetime import datetime, timezone

BASE_DIR = r"C:\Users\Felipe\Documents\coding\montreal"
OUT_MD = os.path.join(BASE_DIR, "TELEMETRY_STATUS.md")
BRAIN_DIR = r"C:\Users\Felipe\.gemini\antigravity-cli\brain"
PARENT_CID = "46bfcc49-d0cd-4c6f-9b9e-df45a866983f"

ACTIVE_WAVE_SUBAGENTS = [
    ("Subagent 1: Poly Haven Assets", "52a6327d-b600-4c51-bc98-04087790a0a8", "src/download_polyhaven_expansion.py"),
    ("Subagent 2: Google SV & 4K Sat", "56178909-7ba7-489d-a22b-87d87674ec9f", "src/fetch_expanded_streetview_and_satellite.py"),
    ("Subagent 3: Eastern Old Port", "24659148-3c16-425a-aad1-ecfa2a96f313", "src/overhaul_eastern_old_port.py"),
    ("Subagent 4: SW Harbor & Cite du Havre", "a4845cf3-c712-4558-b42a-516d1c8e4da7", "src/overhaul_southwest_harbor_and_cite_du_havre.py"),
    ("Subagent 5: Missing Corridor Bldgs", "0607a805-0ca5-4b1e-87ce-07bb42b4a41f", "src/overhaul_missing_corridor_buildings.py"),
    ("Subagent 6: Streets & Sidewalks", "9127fce3-9299-4c8d-96cd-4bed183dd3a5", "src/overhaul_streets_and_sidewalks.py"),
    ("Subagent 7: Parks & Vegetation", "fd6b873b-3c33-471d-a780-60e5e4e9e672", "src/overhaul_parks_and_vegetation.py"),
    ("Subagent 8: Water & 4K Terrain", "f9fb6122-2c13-48dc-81de-74f5eb73061f", "src/overhaul_water_and_terrain.py"),
]

HISTORICAL_SUBAGENTS = [
    ("Wave 0: Block Builder (MTL-VM-0001)", "2bd4017e-9772-4602-ba39-e85a1dee56de"),
    ("Wave 0: Visual Critic (MTL-VM-0001)", "201464c9-9637-4b00-bd3c-1dc5d54f6f35"),
    ("Wave 1: Team Lead 1 (MTL-VM-0002)", "d1b53e06-b30c-4a77-a643-9a98f8fb4a4b"),
    ("Wave 1: Team Lead 2 (MTL-VM-0003)", "3ad077f3-5364-4d98-bf41-98729a46806f"),
    ("Wave 1: Team Lead 3 (MTL-VM-0004)", "0fbd08d1-18b3-4574-a207-0c726f8b04ef"),
    ("Wave 1: Team Lead 4 (MTL-VM-0005)", "1c9a8a0b-df5b-4bc0-918e-cb1ecc539dd5"),
    ("Wave 1: Team Lead 5 (MTL-VM-0006)", "29331b3a-a7ff-45a8-a2f4-f2fd7e24b34c"),
    ("Wave 1: Uniformity Stitcher", "1612780c-bbb8-4415-b45b-8eb894dac4fb"),
    ("Teamwork: 15-Block Z-Fighting Overhaul", "967e8ec0-08b4-462a-bdcb-cf12b4f82613"),
    ("Teamwork: 25-Block East Expansion", "e8bd9287-0522-4327-9315-258329b13827"),
    ("Teamwork: 35-Block Ring & Water", "6366b024-468d-49d3-b58b-1ddd7a7629eb"),
    ("Benchmark: Flash Lead (MTL-VM-0036 V1)", "de5b6429-86d9-47d2-8866-9dee95d15290"),
    ("Benchmark: Flash Full-Tool (MTL-VM-0036 V2)", "2f35c8c2-158f-4748-99ce-7524d231a50a"),
]


def parse_iso(ts_str: str):
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception:
        return None


def fmt_dur(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    if mins >= 60:
        hrs = mins // 60
        mins = mins % 60
        return f"{hrs}h {mins:02d}m {secs:02d}s"
    return f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"


def analyze_conversation(cid: str, target_rel_path: str = None):
    log_path = os.path.join(BRAIN_DIR, cid, ".system_generated", "logs", "transcript.jsonl")
    if not os.path.exists(log_path):
        return None

    steps = []
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.strip():
                try:
                    steps.append(json.loads(line))
                except Exception:
                    pass
    if not steps:
        return None

    t_start = parse_iso(steps[0].get("created_at", ""))
    t_latest = parse_iso(steps[-1].get("created_at", ""))
    now = datetime.now(timezone.utc)

    in_tok = 0
    out_tok = 0
    cache_tok = 0
    llm_turns = 0
    last_action = "initializing"
    is_done = False
    is_err = False

    for s in steps:
        it = int(s.get("input_tokens", 0) or 0)
        ot = int(s.get("output_tokens", 0) or 0)
        ct = int(s.get("cache_read_tokens", 0) or 0)
        in_tok += it
        out_tok += ot
        cache_tok += ct
        if s.get("type") == "PLANNER_RESPONSE":
            llm_turns += 1
            tcs = s.get("tool_calls", [])
            if tcs:
                last_tc = tcs[-1]
                tname = last_tc.get("name", "")
                args = last_tc.get("arguments", {}) or {}
                summary = args.get("toolSummary") or args.get("Path", "")
                if summary and ("\\" in summary or "/" in summary):
                    summary = os.path.basename(summary)
                last_action = f"`{tname}` ({summary})" if summary else f"`{tname}`"
            else:
                last_action = "Completed final response"

    last_step = steps[-1]
    if last_step.get("type") == "PLANNER_RESPONSE" and not last_step.get("tool_calls"):
        is_done = True
    elif last_step.get("type") == "ERROR_MESSAGE":
        is_err = True
        last_action = "Stream timeout / retried"

    if target_rel_path:
        abs_target = os.path.join(BASE_DIR, target_rel_path)
        if os.path.exists(abs_target) and os.path.getsize(abs_target) > 1000:
            is_done = True
            is_err = False
            sz_kb = os.path.getsize(abs_target) // 1024
            last_action = f"Verified `{target_rel_path}` ({sz_kb} KB)"

    elapsed_s = (t_latest - t_start).total_seconds() if (t_start and t_latest) else 0.0
    wall_s = (now - t_start).total_seconds() if t_start else 0.0
    dur_s = elapsed_s if (is_done or is_err) else wall_s
    state_str = "DONE" if is_done else ("TIMEOUT" if is_err else "RUNNING")

    return {
        "cid": cid,
        "steps": len(steps),
        "llm_turns": llm_turns,
        "status": state_str,
        "duration_s": round(dur_s, 1),
        "input_tokens": in_tok,
        "cache_read_tokens": cache_tok,
        "output_tokens": out_tok,
        "total_tokens": in_tok + out_tok,
        "all_tokens_with_cache": in_tok + cache_tok + out_tok,
        "last_action": last_action,
    }


def generate_markdown_report() -> str:
    now_local = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines = [
        "# Montreal 3D Reconstruction — Live Runtime & Token Telemetry",
        "",
        f"**Last Updated:** `{now_local}` (Auto-refreshed every 60 seconds by `src/telemetry_monitor.py`)",
        "",
        "## 1. Current 8-Subagent Overhaul Wave",
        "",
        "| Subagent / Task | State | Duration | Steps | Uncached Input Tokens | Cache Read Tokens | Output Tokens | Total (In + Out) |Total (incl. Cache) | Deliverable / Status |",
        "| :--- | :---: | :---: | :---: | ---: | ---: | ---: | ---: | ---: | :--- |",
    ]

    w_in, w_cache, w_out, w_steps = 0, 0, 0, 0
    for name, cid, rel_p in ACTIVE_WAVE_SUBAGENTS:
        info = analyze_conversation(cid, rel_p)
        if not info:
            lines.append(f"| {name} | `WAIT` | `0s` | 0 | 0 | 0 | 0 | **0** | 0 | Waiting |")
            continue
        w_in += info["input_tokens"]
        w_cache += info["cache_read_tokens"]
        w_out += info["output_tokens"]
        w_steps += info["steps"]
        lines.append(
            f"| **{name}** (`{cid[:8]}`) | `{info['status']}` | `{fmt_dur(info['duration_s'])}` | {info['steps']} | "
            f"{info['input_tokens']:,} | {info['cache_read_tokens']:,} | {info['output_tokens']:,} | "
            f"**{info['total_tokens']:,}** | {info['all_tokens_with_cache']:,} | {info['last_action']} |"
        )

    lines.append(
        f"| **8-Subagent Wave Subtotal** | — | — | **{w_steps:,}** | **{w_in:,}** | **{w_cache:,}** | **{w_out:,}** | "
        f"**{w_in + w_out:,}** | **{w_in + w_cache + w_out:,}** | *Current parallel wave* |"
    )

    lines.extend([
        "",
        "## 2. Main Coordinator & Previous Subagent Waves (Cumulative Session Totals)",
        "",
        "| Session / Wave | State | Duration | Steps | Uncached Input Tokens | Cache Read Tokens | Output Tokens | Total (In + Out) | Total (incl. Cache) |",
        "| :--- | :---: | :---: | :---: | ---: | ---: | ---: | ---: | ---: |",
    ])

    grand_in, grand_cache, grand_out, grand_steps = w_in, w_cache, w_out, w_steps

    p_info = analyze_conversation(PARENT_CID)
    if p_info:
        grand_in += p_info["input_tokens"]
        grand_cache += p_info["cache_read_tokens"]
        grand_out += p_info["output_tokens"]
        grand_steps += p_info["steps"]
        lines.append(
            f"| **Main Coordinator (`{PARENT_CID[:8]}`)** | `{p_info['status']}` | `{fmt_dur(p_info['duration_s'])}` | {p_info['steps']:,} | "
            f"{p_info['input_tokens']:,} | {p_info['cache_read_tokens']:,} | {p_info['output_tokens']:,} | "
            f"**{p_info['total_tokens']:,}** | {p_info['all_tokens_with_cache']:,} |"
        )

    for hname, hcid in HISTORICAL_SUBAGENTS:
        hinfo = analyze_conversation(hcid)
        if not hinfo:
            continue
        grand_in += hinfo["input_tokens"]
        grand_cache += hinfo["cache_read_tokens"]
        grand_out += hinfo["output_tokens"]
        grand_steps += hinfo["steps"]
        lines.append(
            f"| {hname} (`{hcid[:8]}`) | `{hinfo['status']}` | `{fmt_dur(hinfo['duration_s'])}` | {hinfo['steps']:,} | "
            f"{hinfo['input_tokens']:,} | {hinfo['cache_read_tokens']:,} | {hinfo['output_tokens']:,} | "
            f"**{hinfo['total_tokens']:,}** | {hinfo['all_tokens_with_cache']:,} |"
        )

    lines.append(
        f"| **GRAND TOTAL (All Agents)** | — | — | **{grand_steps:,}** | **{grand_in:,}** | **{grand_cache:,}** | **{grand_out:,}** | "
        f"**{grand_in + grand_out:,}** | **{grand_in + grand_cache + grand_out:,}** |"
    )
    lines.append("")
    return "\n".join(lines)


def write_once():
    md = generate_markdown_report()
    tmp_path = OUT_MD + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(md)
    os.replace(tmp_path, OUT_MD)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true", help="Continuously update TELEMETRY_STATUS.md every N seconds")
    parser.add_argument("--interval", type=int, default=60, help="Refresh interval in seconds (default 60)")
    args = parser.parse_args()

    write_once()
    print(f"Updated {OUT_MD}")

    if args.watch:
        print(f"Watching telemetry and updating {OUT_MD} every {args.interval}s...")
        while True:
            time.sleep(args.interval)
            try:
                write_once()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Updated {OUT_MD}")
            except Exception as e:
                print(f"Telemetry update warning: {e}")


if __name__ == "__main__":
    main()
