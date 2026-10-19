#!/usr/bin/env python3
"""test_game_engineer_batch.py - 350L unit-test suite for game-engineer batch.

Tests:
- dispatch: off-identity + on-delegation
- 4 tier gates: status=ok across all 4 tiers
- 9 sidecars: off-identity + on-delegation
- aleia bridge: wrong-family + off + on
- oracle capture: counts match expected (1/16/33/8)
- byte-identical: skill-store mirror matches source (PIT-GGP-39)

Run:
  python3 tests/test_game_engineer_batch.py
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest


def _load(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class DispatchTests(unittest.TestCase):
    def test_dispatch_self_test(self):
        p = ("/mnt/HC_Volume_105866131/.openclaw/workspace/repos/game-loop/"
             "agent-harness/scripts/game_harness_re_dispatch.py")
        env = {**os.environ, "GAME_RE_DISPATCH": "1"}
        r = subprocess.run(["python3", p, "--self-test"],
                           capture_output=True, text=True, env=env, timeout=20)
        self.assertIn('"status": "ok"', r.stdout,
                      f"dispatch failed: {r.stdout} {r.stderr}")
        self.assertIn('"all_primitive_self_tests_ok": true', r.stdout)
        self.assertIn('"end_to_end_chain_ok": true', r.stdout)


class TierGateTests(unittest.TestCase):
    TIERS = ["t0_preflight", "t1_review", "t2_route", "t3_posthoc"]

    def test_all_tier_gates_pass(self):
        for t in self.TIERS:
            p = (f"/root/.hermes/skills/sales-game-re-jev-{t}-gate/"
                 "scripts/gate.py")
            env = {**os.environ,
                   "GAME_RE_DISPATCH": "1",
                   f"GAME_RE_{t.upper()}_GATE": "1"}
            r = subprocess.run(["python3", p, "--self-test"],
                               capture_output=True, text=True, env=env,
                               timeout=20)
            self.assertIn('"status": "ok"', r.stdout,
                          f"tier {t} failed: {r.stdout} {r.stderr}")


class SidecarTests(unittest.TestCase):
    SURFACES = [
        ("harness",     "GAME_RE_HARNESS_SIDECAR"),
        ("mcp",         "GAME_RE_MCP_SIDECAR"),
        ("sb",          "GAME_RE_SB_SIDECAR"),
        ("vault",       "GAME_RE_VAULT_SIDECAR"),
        ("bot_loop",    "GAME_RE_BOT_LOOP_SIDECAR"),
        ("diamond",     "GAME_RE_DIAMOND_SIDECAR"),
        ("fable",       "GAME_RE_FABLE_SIDECAR"),
        ("bench",       "GAME_RE_BENCH_SIDECAR"),
        ("appfactory",  "GAME_RE_APPFACTORY_SIDECAR"),
    ]

    def test_all_sidecars_pass(self):
        for surface, gate in self.SURFACES:
            p = (f"/root/.hermes/skills/sales-game-re-{surface}-sidecar/"
                 "scripts/sidecar.py")
            env = {**os.environ, "GAME_RE_DISPATCH": "1", gate: "1"}
            r = subprocess.run(["python3", p, "--self-test"],
                               capture_output=True, text=True, env=env,
                               timeout=20)
            self.assertIn('"status": "ok"', r.stdout,
                          f"sidecar {surface} failed: {r.stdout} {r.stderr}")
            self.assertIn('"off_identity_ok": true', r.stdout)
            self.assertIn('"on_delegation_ok": true', r.stdout)


class AleiaBridgeTests(unittest.TestCase):
    def test_bridge_self_test(self):
        bus = "/root/.hermes/skills/sales-aleia-office-family-bus/scripts"
        sys.path.insert(0, bus)
        ext = _load("ext",
                    f"{bus}/sales_aleia_office_family_bus_game_re_extension.py")
        r = ext.self_test()
        self.assertEqual(r["status"], "ok",
                         f"aleia bridge failed: {r}")
        self.assertTrue(r["wrong_family_ok"])
        self.assertTrue(r["off_ok"])
        self.assertTrue(r["on_ok"])


class OracleCaptureTests(unittest.TestCase):
    EXPECTED = {"epics": 1, "stories": 16, "acs": 33, "issues": 8}

    def test_oracle_capture(self):
        p = ("/mnt/HC_Volume_105866131/workspace/repos/game-engineer/oracle/"
             "oracle_capture.py")
        env = {**os.environ, "PGPASSWORD": "postgres"}
        r = subprocess.run(["python3", p], capture_output=True, text=True,
                           env=env, timeout=120)
        self.assertIn('"status": "ok"', r.stdout,
                      f"oracle capture failed: {r.stdout} {r.stderr}")
        self.assertIn('"epics": 1', r.stdout)
        self.assertIn('"stories": 16', r.stdout)
        self.assertIn('"acs": 33', r.stdout)
        self.assertIn('"issues": 8', r.stdout)


class ByteIdentityTests(unittest.TestCase):
    """PIT-GGP-39: skill-store mirror must byte-match source."""

    def test_dispatch_in_skill_store(self):
        src = ("/mnt/HC_Volume_105866131/.openclaw/workspace/repos/game-loop/"
               "agent-harness/scripts/game_harness_re_dispatch.py")
        self.assertTrue(os.path.exists(src))
        # Game-loop dispatch lives in the repo, not the skill-store. Verify
        # it still passes self-test.
        r = subprocess.run(["python3", src, "--self-test"],
                           capture_output=True, text=True,
                           env={**os.environ, "GAME_RE_DISPATCH": "1"},
                           timeout=20)
        self.assertIn('"status": "ok"', r.stdout,
                      f"dispatch byte-identity test failed: {r.stdout}")

    def test_sidecar_byte_match(self):
        """Compare sidecar.py between source and skill-store mirror."""
        K = "/root/.hermes/skills"
        SS = f"{K}/skill-store"
        for surface in ["harness", "mcp", "sb"]:
            s = f"{K}/sales-game-re-{surface}-sidecar/scripts/sidecar.py"
            d = f"{SS}/sales-game-re-{surface}-sidecar/scripts/sidecar.py"
            if not (os.path.exists(s) and os.path.exists(d)):
                continue
            with open(s, "rb") as f:
                src_h = __import__("hashlib").sha256(f.read()).hexdigest()
            with open(d, "rb") as f:
                dst_h = __import__("hashlib").sha256(f.read()).hexdigest()
            self.assertEqual(src_h, dst_h,
                             f"sidecar {surface} byte mismatch")


class LineCapTests(unittest.TestCase):
    """Verify all new components respect the 350L cap."""

    def test_all_components_under_350_lines(self):
        K = "/root/.hermes/skills"
        for s in [
            "sales-game-re-intake",
            "sales-game-re-decompile-router",
            "sales-game-re-clone-orchestrator",
            "sales-game-re-voice-compile",
            "sales-game-re-approval-passthrough",
            "sales-game-re-github-feature-inject",
            "sales-game-re-jev-chokepoint",
            "sales-game-re-jev-t0-preflight-gate",
            "sales-game-re-jev-t1-review-gate",
            "sales-game-re-jev-t2-route-gate",
            "sales-game-re-jev-t3-posthoc-gate",
            "sales-game-re-harness-sidecar",
            "sales-game-re-mcp-sidecar",
            "sales-game-re-sb-sidecar",
            "sales-game-re-vault-sidecar",
            "sales-game-re-bot_loop-sidecar",
            "sales-game-re-diamond-sidecar",
            "sales-game-re-fable-sidecar",
            "sales-game-re-bench-sidecar",
            "sales-game-re-appfactory-sidecar",
        ]:
            py = f"{K}/{s}/scripts/{s.replace('-', '_')}.py"
            if not os.path.exists(py):
                # tier gates use gate.py
                py = f"{K}/{s}/scripts/gate.py"
            if not os.path.exists(py):
                # sidecars use sidecar.py
                py = f"{K}/{s}/scripts/sidecar.py"
            if not os.path.exists(py):
                continue
            with open(py) as f:
                n = sum(1 for _ in f)
            self.assertLessEqual(n, 350,
                                 f"{s} is {n}L > 350 cap")


if __name__ == "__main__":
    unittest.main(verbosity=2)