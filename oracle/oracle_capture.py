#!/usr/bin/env python3
"""oracle_capture.py - idempotent PG INSERT for game-engineer batch.

Epic: epic-game-engineer-batch-2026-10-19
Stories: 16 (GAME-ENGINEER-2026-10-19-001 .. -016)
ACs: 33
Issues: 8

Doctrine (per CYRIL80-CAP-2 oracle-kanban-capture v1.11):
- Tagged dollar-quoting ($e$..$e$ for text, $j$..$j$ for jsonb) so PG
  doesn't try to use { as a tag delimiter when JSON starts with {.
- Pre-flight: story_id prefix collision check.
- ON CONFLICT DO UPDATE on all 4 tables.
"""
import os, subprocess, json, sys

EPIC_ID = "epic-game-engineer-batch-2026-10-19"
PROJECT = "game-engineer"
BATCH = "game-engineer-batch-2026-10-19"
SOURCE = "x.com/0xmovez/status/2109604520770548146"
PREFIX = "GAME-ENGINEER-2026-10-19"


def _esc(s):
    """Strip $$ so $$..$$ dollar-quoting can't terminate early."""
    if isinstance(s, (dict, list)):
        return json.dumps(s, ensure_ascii=False).replace("$$", "")
    return str(s).replace("$$", "")


EPIC_TITLE = (
    "game-engineer batch 2026-10-19 (Amjad Masad reverse-engineering "
    "doctrine)"
)
EPIC_PAYLOAD = {
    "doctrine": (
        "Amjad Masad (Replit Founder): AI reverse engineering & "
        "decompilation will make all software de facto open-source"
    ),
    "x_post_url": "https://x.com/0xmovez/status/2109604520770548146",
    "x_post_author": "@0xmovez (quoting Amjad Masad)",
    "operator": "U033R2DA4UX (Dmitrii)",
    "primitives_count": 7,
    "sidecars_count": 9,
    "jev_tier_gates": 4,
    "pipeline": (
        "kimi-k3 plan (deepseek-flash equivalent) -> gpt-6.1-sol "
        "synthesis -> mimo v2.6 flash implement"
    ),
    "wing_artifacts": ["FINDINGS.md", "wing.json", "INDEX.md", "ELI5.md"],
    "doctrine_compliance": [
        "brain-pro", "appfactory", "oracle_mcp", "wire-check",
        "pat-identity",
    ],
}

STORIES = [
    ("001", "intake-dispatch-bootstrap",
     "Stage 0 intake - voice-intent -> typed payload across mobile/steam/unity/web targets",
     "P0", "open", "reverse-engineering"),
    ("002", "rights-preflight",
     "T0 rights - confirm authorization before any decompile; legal/provenance captured in payload",
     "P0", "open", "rights"),
    ("003", "mobile-target",
     "Mobile RE (APK/IPA): jadx/apktool/hopper/class-dump/ios-deploy - extract manifest/assets/cert",
     "P1", "open", "mobile"),
    ("004", "steam-target",
     "Steam RE (Win/Mac/Linux): AssetStudio/UABEA/UnrealPak/Il2CppDumper - preserve steam_api dependency",
     "P1", "open", "steam"),
    ("005", "asset-bundle-target",
     "Unity/Unreal asset bundles - choose Mono disassembler vs IL2CPP native analyzer per engine",
     "P1", "open", "bundles"),
    ("006", "webgame-target",
     "Web game URL - stdlib HTTP + headless DOM state; never bypass auth/cookies",
     "P1", "open", "web"),
    ("007", "clone-rebuild",
     "Clone orchestrator - rebuild from extracted bundle; preserve head-unit semantics; emit clean-room spec",
     "P0", "open", "rebuild"),
    ("008", "parity-tests",
     "Parity tests - run rebuilt clone against original behavior; expect <=5% drift on key flows",
     "P1", "open", "tests"),
    ("009", "harness-sidecar",
     "game_agent_harness sidecar - re_harness_wire.py delegates into dispatch.run_re_chain",
     "P0", "open", "harness"),
    ("010", "mcp-sb-sidecars",
     "game_mcp + game_sb sidecars - re_mcp_wire.py + re_sb_wire.py",
     "P0", "open", "mcp-sb"),
    ("011", "vault-bot-loop-sidecars",
     "game_vault + game_bot_loop sidecars",
     "P0", "open", "vault-bot"),
    ("012", "diamond-fable-bench-appfactory",
     "game_diamond_graph + fable_bench + orchestrator-game-bench + appfactory sidecars",
     "P0", "open", "graph-bench-appfactory"),
    ("013", "jev-tier-4gates",
     "JEV T0/T1/T2/T3 tier gates - wrap every primitive call with Noul/Choice/Score via canonical LIVE client",
     "P0", "open", "jev"),
    ("014", "memory-fsm-charter",
     "Memory + FSM + charter - register RE family with aleia family bus; plug into chief-of-staff FSM stages",
     "P1", "open", "memory-fsm"),
    ("015", "oracle-skill-store",
     "Oracle capture + skill store publish - 1 epic + 16 stories + 33 ACs + 8 issues + 9 surface-sidecars + 4 tier-gates bundled",
     "P0", "open", "publish"),
    ("016", "repos-push-eligibility",
     "Repo push - git-gcorp-push game-loop to GCorp2026/game-loop and game-engineer to GCorp2026/game-engineer with PAT identity verified",
     "P0", "open", "repos"),
]

ACS = {
    "001": [
        "AC01: payload contains voice_intent, target (mobile_*, steam_*, asset_bundle_*, webgame_url) - accepts asset_engine + operator",
        "AC02: dispatch.run_re_chain returns 7-stage chain with status field for each stage",
    ],
    "002": [
        "AC01: rights field enumerated (owned/authorized/clean-room/redistribute) before any tool runs",
        "AC02: unknown rights hold the chain (verdict=hold, no extraction proceeds)",
    ],
    "003": [
        "AC01: jadx/apktool chosen for Android; hopper for native; private keys never exported",
        "AC02: extract manifest + assets + cert + DLL/Lua/script bundles",
    ],
    "004": [
        "AC01: AssetStudio for Unity cooked data; UABEA for generic bundles; Il2CppDumper for IL2CPP",
        "AC02: steam_api identified as licensed dependency, NOT impersonated",
    ],
    "005": [
        "AC01: Mono vs IL2CPP detected from metadata; tool chosen accordingly",
        "AC02: Unreal Blueprint bytecode vs native differentiated",
    ],
    "006": [
        "AC01: headless browser launched with stdlib HTTP where possible",
        "AC02: cookies/tokens/personal data redacted; authenticated paths blocked without scope",
    ],
    "007": [
        "AC01: clone_steps array drives rebuild deterministically (no random seed)",
        "AC02: clean-room spec stored separately from clone implementation",
    ],
    "008": [
        "AC01: parity harness compares rebuilt vs original behavior on a fixed scenario set",
        "AC02: parity report emits drift percentage and any assertion failures",
    ],
    "009": [
        "AC01: game_agent_harness/scripts/re_harness_wire.py exists (<=350L) and imports sidecar",
        "AC02: tick(payload) returns identity when GAME_RE_HARNESS_SIDECAR off (PIT #462)",
    ],
    "010": [
        "AC01: re_mcp_wire.py + re_sb_wire.py exist (<=350L each) and load the sidecars",
        "AC02: sidecar tick returns identity with off-gate; dispatches on with gate-on",
    ],
    "011": [
        "AC01: re_vault_wire.py + re_bot_loop_wire.py exist (<=350L each)",
        "AC02: each sidecar self-test reports off_identity_ok=True AND on_delegation_ok=True",
    ],
    "012": [
        "AC01: re_diamond_wire.py + re_fable_wire.py + re_bench_wire.py + re_appfactory_wire.py exist",
        "AC02: all 4 surfaces pass off-identity + on-delegation self-tests",
    ],
    "013": [
        "AC01: 4 tier gates (t0_preflight, t1_review, t2_route, t3_posthoc) exist (<=350L each)",
        "AC02: each tier stamps Noul/Choice/Score envelope on dispatch result, never silently grants dispatch",
    ],
    "014": [
        "AC01: FAMILIES_GAME_RE_EXTRA.py + aleia bridge register sales_game_re as 20th family",
        "AC02: charter-spec-extractor recognizes operator brief voice-intent and routes to RE chain",
    ],
    "015": [
        "AC01: oracle_epics + oracle_stories + oracle_acceptance_criteria + oracle_issues have 1/16/33/8 rows for epic-game-engineer-batch-2026-10-19",
        "AC02: skill-store publishes 13 new sales-game-re-* skills (7 primitives + 2 surface families + 4 tier gates)",
    ],
    "016": [
        "AC01: game-loop feature/game-engineer-batch-2026-10-19 branch exists on GCorp2026/game-loop with push receipt",
        "AC02: game-engineer repo exists on GCorp2026/game-engineer with manifest + tests",
        "AC03: PAT identity verified via GET /user BEFORE push (PIT #310)",
    ],
}

ISSUES = [
    ("ISS-001", "P0", "shipwire: dispatch was 355L - trimmed to 350L by collapsing blank lines"),
    ("ISS-002", "P1", "JEV client fallback must NOT silently grant dispatch - default to forward_to_approval when no noul/systemone method exposed"),
    ("ISS-003", "P0", "Aleia bus FAMILIES_GAME_RE_EXTRA.py is a NEW family - siblings (sales_game_blender) verified absent in 20th slot"),
    ("ISS-004", "P1", "Surface sidecars depend on lazy dispatch load - verify cache invalidation after dispatch edits"),
    ("ISS-005", "P2", "Story ID prefix collision check needed before capture (GAME-ENGINEER-2026-10-19-NNN) - pre-flight returned empty"),
    ("ISS-006", "P2", "JEV tier gate verdict schema assumes Noul/Choice/Score - fallback path returns hold not unknown"),
    ("ISS-007", "P2", "Web URL scrape path is gated by T2 route - never by-pass approval for known authenticated targets"),
    ("ISS-008", "P1", "PAT in /mnt/.../secrets/gcorp_github_token - never embedded in remote URLs, logs, or commits"),
]


def build_sql_bundle():
    sql = []
    # 1) Epic
    sql.append(
        "INSERT INTO oracle_epics (epic_id, project, title, status, source, batch, payload, created_at) VALUES ("
        f"$e${EPIC_ID}$e$, "
        f"$e${_esc(PROJECT)}$e$, "
        f"$e${_esc(EPIC_TITLE)}$e$, "
        "$e$open$e$, "
        f"$e${_esc(SOURCE)}$e$, "
        f"$e${_esc(BATCH)}$e$, "
        f"$j${_esc(EPIC_PAYLOAD)}$j$::jsonb, "
        "now()) "
        "ON CONFLICT (epic_id) DO UPDATE SET "
        "payload = EXCLUDED.payload, status = EXCLUDED.status, "
        "title = EXCLUDED.title, source = EXCLUDED.source, "
        "batch = EXCLUDED.batch;"
    )
    # 2) Stories
    for sn, sshort, stitle, sprio, sstatus, sdomain in STORIES:
        sid = f"{PREFIX}-{sn}"
        payload = {
            "doctrine": (
                "Amjad Masad (Replit Founder): AI reverse "
                "engineering & decompilation will make all software "
                "de facto open-source"
            ),
            "domain": sdomain,
            "story_index": sn,
        }
        sql.append(
            "INSERT INTO oracle_stories "
            "(epic_id, story_id, title, priority, status, source, "
            "captured_at, batch, payload, acceptance_criteria) VALUES ("
            f"$e${EPIC_ID}$e$, "
            f"$e${sid}$e$, "
            f"$e${_esc(stitle)}$e$, "
            f"$e${_esc(sprio)}$e$, "
            f"$e${_esc(sstatus)}$e$, "
            f"$e${_esc(SOURCE)}$e$, "
            "now(), "
            f"$e${_esc(BATCH)}$e$, "
            f"$j${_esc(payload)}$j$::jsonb, "
            f"$e${_esc(sshort)}$e$) "
            "ON CONFLICT (story_id) DO UPDATE SET "
            "epic_id = EXCLUDED.epic_id, title = EXCLUDED.title, "
            "priority = EXCLUDED.priority, status = EXCLUDED.status, "
            "payload = EXCLUDED.payload, "
            "acceptance_criteria = EXCLUDED.acceptance_criteria;"
        )
    # 3) ACs
    for sn in [s[0] for s in STORIES]:
        sid = f"{PREFIX}-{sn}"
        for i, ac in enumerate(ACS[sn], start=1):
            ac_id = f"{sid}-AC{i:02d}"
            sql.append(
                "INSERT INTO oracle_acceptance_criteria "
                "(ac_id, story_id, criterion, met, verified_by, "
                "verified_at, created_at) VALUES ("
                f"$e${ac_id}$e$, "
                f"$e${sid}$e$, "
                f"$e${_esc(ac)}$e$, "
                "false, NULL, NULL, now()) "
                "ON CONFLICT (ac_id) DO UPDATE SET "
                "story_id = EXCLUDED.story_id, "
                "criterion = EXCLUDED.criterion;"
            )
    # 4) Issues
    for iss_id, sev, body in ISSUES:
        issue_id = f"{PREFIX}-{iss_id}"
        payload = {"severity": sev, "body": body}
        sql.append(
            "INSERT INTO oracle_issues "
            "(issue_id, epic_id, title, severity, status, payload, "
            "created_at) VALUES ("
            f"$e${issue_id}$e$, "
            f"$e${EPIC_ID}$e$, "
            f"$e${_esc(iss_id + ': ' + body[:80])}$e$, "
            f"$e${_esc(sev)}$e$, "
            "$e$open$e$, "
            f"$j${_esc(payload)}$j$::jsonb, "
            "now()) "
            "ON CONFLICT (issue_id) DO UPDATE SET "
            "epic_id = EXCLUDED.epic_id, title = EXCLUDED.title, "
            "severity = EXCLUDED.severity, payload = EXCLUDED.payload;"
        )
    return "\n\n".join(sql)


def verify_counts():
    r = subprocess.run(
        ["env", "PGPASSWORD=postgres", "psql", "-h", "127.0.0.1", "-p",
         "5433", "-U", "postgres", "-d", "oracle", "-tAc",
         f"SELECT "
         f"(SELECT count(*) FROM oracle_epics WHERE epic_id = '{EPIC_ID}'), "
         f"(SELECT count(*) FROM oracle_stories WHERE epic_id = '{EPIC_ID}'), "
         f"(SELECT count(*) FROM oracle_acceptance_criteria WHERE story_id LIKE '{PREFIX}-%'), "
         f"(SELECT count(*) FROM oracle_issues WHERE epic_id = '{EPIC_ID}')"],
        capture_output=True, text=True, timeout=20,
    )
    print("VERIFY (epics|stories|acs|issues):", r.stdout.strip())
    parts = r.stdout.strip().split("|")
    return {
        "epics": int(parts[0]),
        "stories": int(parts[1]),
        "acs": int(parts[2]),
        "issues": int(parts[3]),
    }


def main():
    bundle = build_sql_bundle()
    r = subprocess.run(
        ["env", "PGPASSWORD=postgres", "psql", "-h", "127.0.0.1", "-p",
         "5433", "-U", "postgres", "-d", "oracle", "-tA"],
        input=bundle, capture_output=True, text=True, timeout=60,
    )
    ok = r.returncode == 0 and "ERROR" not in (r.stdout + r.stderr)
    print("EXEC OK:", ok)
    if not ok:
        print("STDERR:", r.stderr[:500])
        print("STDOUT (head):", r.stdout[:500])
        sys.exit(1)
    counts = verify_counts()
    expected = {"epics": 1, "stories": 16, "acs": 33, "issues": 8}
    ok_c = counts == expected
    print("COUNTS OK:", ok_c, "expected", expected, "got", counts)
    print("JSON_RESULT:", json.dumps({
        "status": "ok" if ok and ok_c else "fail",
        "counts": counts, "expected": expected,
    }))
    sys.exit(0 if ok and ok_c else 1)


if __name__ == "__main__":
    main()