"""
Resolver — bridges account-agnostic gold labels to a live deployment.

Gold labels must never hardcode physical AWS IDs (``sg-0abc…``), because those
change in every customer account. Instead they reference resources by **stable
handles** that the resolver expands against the environment manifest
(``benchmark/env_manifest.json``) produced by ``runner.provisioner``.

Two handle forms are supported in gold-label ``correct_resources`` /
``should_not_flag`` / tool params:

  "{{stack:OutputKey}}"   explicit CFN output reference, e.g.
                          "{{wafr-nc-kms:WartestkmsKeyId}}"  → "1e00…"
  "{{output_key}}"        short form matched on OutputKey alone when unambiguous,
                          e.g. "{{SecurityGroupId}}"

Plain strings with no ``{{…}}`` are treated as **literal** values and passed
through unchanged (back-compat with legacy labels and free-text resource names).

The resolver is deliberately lenient: an unresolvable handle is returned verbatim
and recorded in ``unresolved`` so the evaluator can surface "this scenario's
fixture is not deployed" rather than silently scoring zero.
"""

import re
from pathlib import Path

_HANDLE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


class ManifestResolver:
    def __init__(self, manifest: dict):
        self.manifest = manifest or {}
        resources = self.manifest.get("resources", [])
        # exact "<stack>:<OutputKey>" -> id
        self._by_key = {r["key"]: r["id"] for r in resources}
        # bare OutputKey -> [ids]  (for short-form / ambiguity detection)
        self._by_output_key: dict[str, list[str]] = {}
        for r in resources:
            self._by_output_key.setdefault(r["output_key"], []).append(r["id"])
        self.unresolved: list[str] = []

    # ── single value ────────────────────────────────────────────────────────
    def resolve(self, value):
        """Expand any {{handle}} inside a string. Non-strings pass through."""
        if not isinstance(value, str):
            return value
        if "{{" not in value:
            return value  # literal

        def _sub(m):
            handle = m.group(1)
            if handle in self._by_key:              # {{stack:OutputKey}}
                return self._by_key[handle]
            ids = self._by_output_key.get(handle)   # {{OutputKey}}
            if ids and len(ids) == 1:
                return ids[0]
            self.unresolved.append(handle)
            return m.group(0)  # leave verbatim

        return _HANDLE.sub(_sub, value)

    # ── collections ─────────────────────────────────────────────────────────
    def resolve_list(self, values) -> list:
        return [self.resolve(v) for v in (values or [])]

    def resolve_params(self, params: dict) -> dict:
        return {k: self.resolve(v) for k, v in (params or {}).items()}

    def resolve_gold(self, gold: dict) -> dict:
        """Return a copy of a gold label with all resource handles resolved."""
        g = dict(gold)
        g["correct_resources"] = self.resolve_list(gold.get("correct_resources"))
        g["should_not_flag"] = self.resolve_list(gold.get("should_not_flag"))
        expected = []
        for tc in gold.get("expected_tools", gold.get("expected_tool_calls", [])):
            tc = dict(tc)
            tc["params"] = self.resolve_params(tc.get("params", {}))
            expected.append(tc)
        # normalize onto the agnostic field name
        g["expected_tools"] = expected
        g["_unresolved"] = list(dict.fromkeys(self.unresolved))
        return g


def load_resolver(manifest_path: Path | None = None) -> ManifestResolver:
    """Build a resolver from the on-disk manifest, or an empty (pass-through) one."""
    from runner.provisioner import load_manifest, MANIFEST_PATH
    path = manifest_path or MANIFEST_PATH
    try:
        manifest = load_manifest(path)
    except FileNotFoundError:
        manifest = {}
    return ManifestResolver(manifest)
