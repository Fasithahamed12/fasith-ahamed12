"""PIVL v0.1 - single-file reference implementation.

Persistent Instruction Verification Loop for enforcing standing constraints
around long-running agent actions. This reference module is model-agnostic.
"""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional


@dataclass
class Rule:
    id: str
    text: str
    priority: int = 50
    scope: str = "global"
    phase: str = "pre"
    active: bool = True
    check_type: str = "semantic"
    check_config: Dict[str, Any] = field(default_factory=dict)
    source: str = "user"
    supersedes: Optional[str] = None


@dataclass
class Failure:
    id: str
    rule_id: str
    action_name: str
    reason: str
    phase: str
    turn: int


@dataclass
class Action:
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckResult:
    rule_id: str
    passed: bool
    reason: str


@dataclass
class VerificationReport:
    allowed: bool
    checks: List[CheckResult]

    @property
    def failures(self) -> List[CheckResult]:
        return [c for c in self.checks if not c.passed]


@dataclass
class EngineResult:
    executed: bool
    action: Action
    pre_report: VerificationReport
    post_report: Optional[VerificationReport] = None
    output: Any = None
    created_failure_ids: List[str] = field(default_factory=list)


class SQLiteRegistry:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS rules(
              id TEXT PRIMARY KEY,
              text TEXT NOT NULL,
              priority INTEGER NOT NULL,
              scope TEXT NOT NULL,
              phase TEXT NOT NULL,
              active INTEGER NOT NULL,
              check_type TEXT NOT NULL,
              check_config TEXT NOT NULL,
              source TEXT NOT NULL,
              supersedes TEXT
            );
            CREATE TABLE IF NOT EXISTS failures(
              id TEXT PRIMARY KEY,
              rule_id TEXT NOT NULL,
              action_name TEXT NOT NULL,
              reason TEXT NOT NULL,
              phase TEXT NOT NULL,
              turn INTEGER NOT NULL
            );
            """
        )
        self.conn.commit()

    @staticmethod
    def make_id(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    def add_rule(self, rule: Rule) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO rules VALUES (?,?,?,?,?,?,?,?,?,?)",
            (rule.id, rule.text, rule.priority, rule.scope, rule.phase,
             int(rule.active), rule.check_type, json.dumps(rule.check_config),
             rule.source, rule.supersedes),
        )
        self.conn.commit()

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        row = self.conn.execute("SELECT * FROM rules WHERE id=?", (rule_id,)).fetchone()
        return self._row_to_rule(row) if row else None

    def list_rules(self, *, active_only: bool = False) -> List[Rule]:
        q = "SELECT * FROM rules" + (" WHERE active=1" if active_only else "")
        q += " ORDER BY priority DESC, id"
        return [self._row_to_rule(r) for r in self.conn.execute(q).fetchall()]

    def add_failure(self, failure: Failure) -> None:
        self.conn.execute(
            "INSERT INTO failures VALUES (?,?,?,?,?,?)",
            (failure.id, failure.rule_id, failure.action_name, failure.reason,
             failure.phase, failure.turn),
        )
        self.conn.commit()

    def list_failures(self) -> List[Failure]:
        rows = self.conn.execute("SELECT * FROM failures ORDER BY turn,id").fetchall()
        return [Failure(**dict(r)) for r in rows]

    @staticmethod
    def _row_to_rule(row: sqlite3.Row) -> Rule:
        return Rule(
            id=row["id"], text=row["text"], priority=row["priority"],
            scope=row["scope"], phase=row["phase"], active=bool(row["active"]),
            check_type=row["check_type"], check_config=json.loads(row["check_config"]),
            source=row["source"], supersedes=row["supersedes"],
        )


class RuleCompiler:
    EQ = re.compile(r"^(?P<key>[A-Za-z_][\w.]*)\s+must\s+equal\s+(?P<value>.+)$", re.I)
    EXISTS = re.compile(r"^(?P<key>[A-Za-z_][\w.]*)\s+must\s+exist$", re.I)
    NOT_EXISTS = re.compile(r"^(?P<key>[A-Za-z_][\w.]*)\s+must\s+not\s+exist$", re.I)
    BEFORE = re.compile(r"^before\s+(?P<action>[\w.-]+),\s*(?P<key>[A-Za-z_][\w.]*)\s+must\s+equal\s+(?P<value>.+)$", re.I)
    FORBID = re.compile(r"^never\s+(?P<action>[\w.-]+)$", re.I)

    def compile(self, text: str, *, scope: str = "global", priority: int = 50) -> Rule:
        raw, rid = text.strip().rstrip("."), SQLiteRegistry.make_id("R")
        m = self.BEFORE.match(raw)
        if m:
            return Rule(rid, text, priority, scope, "pre", True, "before_equals",
                        {"action": m.group("action"), "key": m.group("key"),
                         "expected": self._coerce(m.group("value"))})
        m = self.EQ.match(raw)
        if m:
            return Rule(rid, text, priority, scope, "both", True, "equals",
                        {"key": m.group("key"), "expected": self._coerce(m.group("value"))})
        m = self.EXISTS.match(raw)
        if m:
            return Rule(rid, text, priority, scope, "both", True, "exists", {"key": m.group("key")})
        m = self.NOT_EXISTS.match(raw)
        if m:
            return Rule(rid, text, priority, scope, "both", True, "not_exists", {"key": m.group("key")})
        m = self.FORBID.match(raw)
        if m:
            return Rule(rid, text, priority, scope, "pre", True, "forbid_action", {"action": m.group("action")})
        return Rule(rid, text, priority, scope, "both", True, "semantic", {})

    @staticmethod
    def _coerce(value: str) -> Any:
        v = value.strip().strip('"\'')
        lv = v.lower()
        if lv == "true": return True
        if lv == "false": return False
        if lv in {"none", "null"}: return None
        try: return float(v) if "." in v else int(v)
        except ValueError: return v


SemanticVerifier = Callable[[Rule, Action, Dict[str, Any], str], CheckResult]


class Verifier:
    def __init__(self, semantic_verifier: Optional[SemanticVerifier] = None) -> None:
        self.semantic_verifier = semantic_verifier

    def verify(self, rules: Iterable[Rule], action: Action, state: Dict[str, Any], phase: str) -> VerificationReport:
        checks = [self._check(r, action, state, phase) for r in rules if r.active and r.phase in {phase, "both"}]
        return VerificationReport(all(c.passed for c in checks), checks)

    def _check(self, rule: Rule, action: Action, state: Dict[str, Any], phase: str) -> CheckResult:
        c, t = rule.check_config, rule.check_type
        if t == "equals":
            actual = self._get(state, c["key"]); ok = actual == c["expected"]
            return CheckResult(rule.id, ok, f"{c['key']}={actual!r}, expected {c['expected']!r}")
        if t == "exists":
            ok = self._has(state, c["key"]); return CheckResult(rule.id, ok, f"{c['key']} must exist")
        if t == "not_exists":
            ok = not self._has(state, c["key"]); return CheckResult(rule.id, ok, f"{c['key']} must not exist")
        if t == "forbid_action":
            ok = action.name != c["action"]; return CheckResult(rule.id, ok, f"action {c['action']} is forbidden")
        if t == "before_equals":
            if action.name != c["action"]: return CheckResult(rule.id, True, "rule not triggered by this action")
            actual = self._get(state, c["key"]); ok = actual == c["expected"]
            return CheckResult(rule.id, ok, f"before {action.name}: {c['key']}={actual!r}, expected {c['expected']!r}")
        if t == "require_rule_pass":
            return CheckResult(rule.id, True, f"prevention reminder for {c['rule_id']}")
        if t == "semantic":
            if self.semantic_verifier: return self.semantic_verifier(rule, action, state, phase)
            return CheckResult(rule.id, False, "semantic rule requires a semantic_verifier adapter")
        return CheckResult(rule.id, False, f"unknown check_type={t}")

    @staticmethod
    def _get(state: Dict[str, Any], dotted: str, missing: Any = None) -> Any:
        cur: Any = state
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur: return missing
            cur = cur[part]
        return cur

    @staticmethod
    def _has(state: Dict[str, Any], dotted: str) -> bool:
        sentinel = object(); return Verifier._get(state, dotted, sentinel) is not sentinel


class InstructionRouter:
    def __init__(self, registry: SQLiteRegistry) -> None:
        self.registry = registry

    def route(self, action: Action, *, scope: str = "global") -> List[Rule]:
        failures = self.registry.list_failures()
        failed_ids = {f.rule_id for f in failures if f.action_name == action.name}
        rules = [r for r in self.registry.list_rules(active_only=True) if r.scope in {"global", scope}]
        def score(r: Rule) -> tuple[int, int]:
            trigger = int(r.check_config.get("action") == action.name)
            previously_failed = int(r.id in failed_ids or r.source == "failure-derived")
            return (r.priority + 30 * trigger + 20 * previously_failed, trigger)
        return sorted(rules, key=score, reverse=True)


Executor = Callable[[Action, Dict[str, Any]], Any]


class PIVLEngine:
    def __init__(self, registry: SQLiteRegistry, verifier: Verifier, router: Optional[InstructionRouter] = None) -> None:
        self.registry, self.verifier = registry, verifier
        self.router = router or InstructionRouter(registry)
        self.turn = 0

    def step(self, action: Action, state: Dict[str, Any], executor: Executor, *, scope: str = "global") -> EngineResult:
        self.turn += 1
        rules = self.router.route(action, scope=scope)
        pre = self.verifier.verify(rules, action, state, "pre")
        failure_ids: List[str] = []
        if not pre.allowed:
            failure_ids.extend(self._record_failures(pre.failures, action, "pre"))
            return EngineResult(False, action, pre, created_failure_ids=failure_ids)
        output = executor(action, state)
        if isinstance(output, dict) and output is not state:
            state.clear(); state.update(output)
        post = self.verifier.verify(rules, action, state, "post")
        if not post.allowed:
            failure_ids.extend(self._record_failures(post.failures, action, "post"))
        return EngineResult(True, action, pre, post, output, failure_ids)

    def _record_failures(self, checks: Iterable[CheckResult], action: Action, phase: str) -> List[str]:
        ids=[]
        for check in checks:
            fid=SQLiteRegistry.make_id("F")
            failure=Failure(fid, check.rule_id, action.name, check.reason, phase, self.turn)
            self.registry.add_failure(failure); ids.append(fid); self._ensure_prevention_rule(failure)
        return ids

    def _ensure_prevention_rule(self, failure: Failure) -> None:
        prevention_id=f"P_{failure.rule_id}_{failure.action_name}"
        if self.registry.get_rule(prevention_id): return
        base=self.registry.get_rule(failure.rule_id)
        self.registry.add_rule(Rule(
            id=prevention_id,
            text=f"Prevention rule derived from failure {failure.id}: before {failure.action_name}, re-check rule {failure.rule_id}.",
            priority=min(100,(base.priority if base else 50)+20),
            scope=base.scope if base else "global", phase="pre", check_type="require_rule_pass",
            check_config={"rule_id": failure.rule_id, "action": failure.action_name}, source="failure-derived"))
