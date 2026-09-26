#!/usr/bin/env python3
"""Create and validate Sol/Luna work packets and evidence receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = 1
PACKET_WORD_LIMIT = 400
RECEIPT_WORD_LIMIT = 300
MAX_CONCURRENT_WORKERS = 7  # Sol is the primary session and is not counted.
STATUSES = {"PASS", "FIX", "BLOCKED"}
RISKS = {"low", "medium", "high"}
PACKET_FIELDS = {
    "schema_version", "packet_id", "objective", "done_when", "owner",
    "owned_paths", "do_not_touch", "inputs", "validation", "risk",
    "return_format", "status", "created_at", "packet_digest",
}
RECEIPT_FIELDS = {
    "schema_version", "packet_id", "status", "summary", "changed_files",
    "commands", "evidence", "risks", "candidate_digest", "next_action",
    "created_at", "packet_digest", "receipt_digest",
}
RUN_FIELDS = {
    "schema_version", "goal", "acceptance", "candidate_digest",
    "max_concurrent_workers", "created_at", "run_digest",
}


class ContractError(ValueError):
    """Raised when an orchestration contract is invalid."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def word_count(value: Any) -> int:
    def strings(item: Any) -> list[str]:
        if isinstance(item, str):
            return [item]
        if isinstance(item, list):
            result: list[str] = []
            for child in item:
                result.extend(strings(child))
            return result
        if isinstance(item, dict):
            result = []
            for child in item.values():
                result.extend(strings(child))
            return result
        return []

    return sum(len(re.findall(r"\S+", text)) for text in strings(value))


def normalize_relative_path(raw: str) -> str:
    text = raw.strip().replace("\\", "/")
    is_dir = text.endswith("/")
    path = PurePosixPath(text)
    if not text or path.is_absolute() or re.match(r"^[A-Za-z]:", text):
        raise ContractError(f"path must be relative: {raw!r}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ContractError(f"path contains unsafe segments: {raw!r}")
    normalized = path.as_posix()
    return normalized + "/" if is_dir else normalized


def paths_overlap(left: str, right: str) -> bool:
    a = normalize_relative_path(left).rstrip("/")
    b = normalize_relative_path(right).rstrip("/")
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def path_is_owned(path: str, owned_paths: list[str]) -> bool:
    normalized = normalize_relative_path(path).rstrip("/")
    for owned in owned_paths:
        scope = normalize_relative_path(owned)
        if scope.endswith("/"):
            prefix = scope.rstrip("/")
            if normalized == prefix or normalized.startswith(prefix + "/"):
                return True
        elif normalized == scope:
            return True
    return False


def require_string(value: dict[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ContractError(f"{key} must be a non-empty string")
    return item


def require_string_list(value: dict[str, Any], key: str, *, allow_empty: bool = True) -> list[str]:
    item = value.get(key)
    if not isinstance(item, list) or any(not isinstance(entry, str) or not entry.strip() for entry in item):
        raise ContractError(f"{key} must be a list of non-empty strings")
    if not allow_empty and not item:
        raise ContractError(f"{key} must not be empty")
    return item


def reject_unknown_fields(value: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ContractError(f"{label} contains unknown fields: {', '.join(unknown)}")


def require_datetime(value: dict[str, Any], key: str) -> str:
    text = require_string(value, key)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{key} must be an ISO 8601 date-time") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{key} must include a timezone")
    return text


def validate_run_contract(run: dict[str, Any]) -> None:
    reject_unknown_fields(run, RUN_FIELDS, "run")
    if run.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("unsupported run schema_version")
    require_string(run, "goal")
    require_string(run, "acceptance")
    require_string(run, "candidate_digest")
    if run.get("max_concurrent_workers") != MAX_CONCURRENT_WORKERS:
        raise ContractError(f"max_concurrent_workers must be {MAX_CONCURRENT_WORKERS}")
    require_datetime(run, "created_at")
    observed = require_string(run, "run_digest")
    unsigned = dict(run)
    unsigned.pop("run_digest")
    if observed != digest(unsigned):
        raise ContractError("run_digest does not match run content")


def validate_packet(packet: dict[str, Any]) -> None:
    reject_unknown_fields(packet, PACKET_FIELDS, "packet")
    if packet.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("unsupported packet schema_version")
    require_string(packet, "packet_id")
    require_string(packet, "objective")
    require_string_list(packet, "done_when", allow_empty=False)
    owner = packet.get("owner")
    if not isinstance(owner, dict):
        raise ContractError("owner must be an object")
    require_string(owner, "agent")
    require_string(owner, "role")
    owned = require_string_list(packet, "owned_paths")
    forbidden = require_string_list(packet, "do_not_touch")
    require_string_list(packet, "inputs")
    require_string_list(packet, "validation", allow_empty=False)
    if packet.get("risk") not in RISKS:
        raise ContractError(f"risk must be one of {sorted(RISKS)}")
    if packet.get("return_format") != "receipt-v1":
        raise ContractError("return_format must be receipt-v1")
    if packet.get("status") not in {"pending", "in_progress"}:
        raise ContractError("packet status must be pending or in_progress")
    require_datetime(packet, "created_at")
    for candidate in owned + forbidden:
        normalize_relative_path(candidate)
    for left in owned:
        for right in forbidden:
            if paths_overlap(left, right):
                raise ContractError(f"owned path {left!r} overlaps do_not_touch path {right!r}")
    countable = {
        "objective": packet["objective"],
        "done_when": packet["done_when"],
        "owner": owner,
        "owned_paths": owned,
        "do_not_touch": forbidden,
        "inputs": packet["inputs"],
        "validation": packet["validation"],
    }
    count = word_count(countable)
    if count > PACKET_WORD_LIMIT:
        raise ContractError(f"packet has {count} words; limit is {PACKET_WORD_LIMIT}")
    if "packet_digest" in packet:
        unsigned = dict(packet)
        observed = unsigned.pop("packet_digest")
        if observed != digest(unsigned):
            raise ContractError("packet_digest does not match packet content")


def validate_receipt(receipt: dict[str, Any], packet: dict[str, Any]) -> None:
    reject_unknown_fields(receipt, RECEIPT_FIELDS, "receipt")
    if receipt.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("unsupported receipt schema_version")
    if require_string(receipt, "packet_id") != packet["packet_id"]:
        raise ContractError("receipt packet_id does not match packet")
    status = receipt.get("status")
    if status not in STATUSES:
        raise ContractError(f"receipt status must be one of {sorted(STATUSES)}")
    require_string(receipt, "summary")
    changed = require_string_list(receipt, "changed_files")
    commands = receipt.get("commands")
    if not isinstance(commands, list):
        raise ContractError("commands must be a list")
    for command in commands:
        if not isinstance(command, dict):
            raise ContractError("each command must be an object")
        require_string(command, "command")
        if not isinstance(command.get("exit_code"), int):
            raise ContractError("each command exit_code must be an integer")
    evidence = receipt.get("evidence")
    if not isinstance(evidence, list):
        raise ContractError("evidence must be a list")
    for item in evidence:
        if not isinstance(item, dict):
            raise ContractError("each evidence item must be an object")
        require_string(item, "kind")
        require_string(item, "path")
    require_string_list(receipt, "risks")
    require_string(receipt, "candidate_digest")
    require_string(receipt, "next_action")
    require_datetime(receipt, "created_at")
    observed_packet_digest = require_string(receipt, "packet_digest")
    expected_packet_digest = packet.get("packet_digest") or digest(packet)
    if observed_packet_digest != expected_packet_digest:
        raise ContractError("receipt packet_digest does not match the work packet")
    for path in changed:
        if not path_is_owned(path, packet["owned_paths"]):
            raise ContractError(f"changed file {path!r} is outside owned_paths")
    if status == "PASS":
        if not evidence:
            raise ContractError("PASS requires at least one evidence item")
        failed = [item for item in commands if item["exit_code"] != 0]
        if failed:
            raise ContractError("PASS cannot contain a failed command")
    if word_count(receipt) > RECEIPT_WORD_LIMIT:
        raise ContractError(f"receipt exceeds {RECEIPT_WORD_LIMIT} words")
    if "receipt_digest" in receipt:
        unsigned = dict(receipt)
        observed = unsigned.pop("receipt_digest")
        if observed != digest(unsigned):
            raise ContractError("receipt_digest does not match receipt content")


def load_packets(run_dir: Path) -> dict[str, dict[str, Any]]:
    packets: dict[str, dict[str, Any]] = {}
    for path in sorted((run_dir / "packets").glob("*.json")):
        packet = read_json(path)
        validate_packet(packet)
        packet_id = packet["packet_id"]
        if packet_id in packets:
            raise ContractError(f"duplicate packet_id: {packet_id}")
        packets[packet_id] = packet
    return packets


def validate_ownership(packets: dict[str, dict[str, Any]]) -> None:
    entries: list[tuple[str, str]] = []
    for packet_id, packet in packets.items():
        for path in packet["owned_paths"]:
            for other_id, other_path in entries:
                if paths_overlap(path, other_path):
                    raise ContractError(
                        f"ownership overlap: {packet_id}:{path} conflicts with {other_id}:{other_path}"
                    )
            entries.append((packet_id, path))


def command_init(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ContractError(f"run directory is not empty: {run_dir}")
    for name in ("packets", "receipts", "evidence"):
        (run_dir / name).mkdir(parents=True, exist_ok=True)
    run = {
        "schema_version": SCHEMA_VERSION,
        "goal": args.goal,
        "acceptance": args.acceptance,
        "candidate_digest": args.candidate_digest or "unfrozen",
        "max_concurrent_workers": MAX_CONCURRENT_WORKERS,
        "created_at": utc_now(),
    }
    run["run_digest"] = digest(run)
    write_json(run_dir / "run.json", run)
    print(run_dir)
    return 0


def command_packet(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    if not (run_dir / "run.json").exists():
        raise ContractError(f"missing run.json in {run_dir}")
    packet = {
        "schema_version": SCHEMA_VERSION,
        "packet_id": args.id,
        "objective": args.objective,
        "done_when": args.done_when,
        "owner": {"agent": args.agent, "role": args.role},
        "owned_paths": [normalize_relative_path(item) for item in args.owned_path],
        "do_not_touch": [normalize_relative_path(item) for item in args.do_not_touch],
        "inputs": args.input,
        "validation": args.validation,
        "risk": args.risk,
        "return_format": "receipt-v1",
        "status": "pending",
        "created_at": utc_now(),
    }
    validate_packet(packet)
    packet["packet_digest"] = digest(packet)
    destination = run_dir / "packets" / f"{args.id}.json"
    if destination.exists():
        raise ContractError(f"packet already exists: {destination}")
    existing = load_packets(run_dir)
    existing[args.id] = packet
    validate_ownership(existing)
    write_json(destination, packet)
    print(destination)
    return 0


def parse_command(raw: str) -> dict[str, Any]:
    try:
        command, code = raw.rsplit("::", 1)
        return {"command": command, "exit_code": int(code)}
    except (ValueError, TypeError) as exc:
        raise ContractError(f"command must use COMMAND::EXIT_CODE: {raw!r}") from exc


def parse_evidence(raw: str) -> dict[str, str]:
    try:
        kind, path = raw.split(":", 1)
    except ValueError as exc:
        raise ContractError(f"evidence must use KIND:PATH: {raw!r}") from exc
    if not kind or not path:
        raise ContractError(f"evidence must use KIND:PATH: {raw!r}")
    return {"kind": kind, "path": path}


def command_receipt(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    packet_path = run_dir / "packets" / f"{args.packet_id}.json"
    packet = read_json(packet_path)
    validate_packet(packet)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "packet_id": args.packet_id,
        "status": args.status,
        "summary": args.summary,
        "changed_files": [normalize_relative_path(item) for item in args.changed_file],
        "commands": [parse_command(item) for item in args.command],
        "evidence": [parse_evidence(item) for item in args.evidence],
        "risks": args.risk,
        "candidate_digest": args.candidate_digest,
        "next_action": args.next_action,
        "created_at": utc_now(),
        "packet_digest": packet.get("packet_digest", digest(packet)),
    }
    validate_receipt(receipt, packet)
    receipt["receipt_digest"] = digest(receipt)
    destination = run_dir / "receipts" / f"{args.packet_id}.json"
    write_json(destination, receipt)
    print(destination)
    return 0


def validate_run(run_dir: Path) -> dict[str, Any]:
    run = read_json(run_dir / "run.json")
    validate_run_contract(run)
    packets = load_packets(run_dir)
    validate_ownership(packets)
    results: list[dict[str, str]] = []
    for packet_id, packet in packets.items():
        receipt_path = run_dir / "receipts" / f"{packet_id}.json"
        if receipt_path.exists():
            receipt = read_json(receipt_path)
            validate_receipt(receipt, packet)
            frozen = run.get("candidate_digest")
            if frozen and frozen != "unfrozen" and receipt["candidate_digest"] != frozen:
                raise ContractError(
                    f"stale evidence for {packet_id}: receipt candidate {receipt['candidate_digest']!r} != run candidate {frozen!r}"
                )
            state = receipt["status"]
        else:
            state = packet["status"]
        results.append({"packet_id": packet_id, "state": state})
    orphan_receipts = sorted(
        path.stem for path in (run_dir / "receipts").glob("*.json") if path.stem not in packets
    )
    if orphan_receipts:
        raise ContractError(f"orphan receipts: {', '.join(orphan_receipts)}")
    return {
        "run": str(run_dir),
        "goal": run.get("goal", ""),
        "candidate_digest": run.get("candidate_digest", ""),
        "packets": results,
        "counts": {
            state: sum(1 for item in results if item["state"] == state)
            for state in ["pending", "in_progress", "PASS", "FIX", "BLOCKED"]
        },
    }


def command_validate(args: argparse.Namespace) -> int:
    result = validate_run(Path(args.run_dir))
    print(json.dumps({"valid": True, **result}, indent=2, ensure_ascii=False))
    return 0


def command_summary(args: argparse.Namespace) -> int:
    result = validate_run(Path(args.run_dir))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def route(args: argparse.Namespace) -> dict[str, Any]:
    reasons: list[str] = []
    if args.risk == "high":
        lane = "sol"
        reasons.append("high-risk judgment remains with Sol")
    elif args.ambiguity == "high":
        lane = "sol"
        reasons.append("high ambiguity requires primary judgment")
    elif args.ambiguity == "medium" or args.cross_module:
        lane = "sol"
        reasons.append("ambiguity or cross-module reasoning returns to GPT-6 Sol")
    elif args.available_workers == 0:
        lane = "direct"
        reasons.append("no live worker capacity is available")
    elif args.tiny:
        lane = "direct"
        reasons.append("delegation overhead would dominate")
    elif args.parallel_scopes >= 2 and args.ownership_disjoint and args.available_workers >= 2:
        lane = "luna_wave"
        reasons.append("independent disjoint scopes can run concurrently")
    else:
        lane = "luna_single"
        reasons.append("bounded routine work fits one Luna worker")
    return {
        "lane": lane,
        "max_workers": min(MAX_CONCURRENT_WORKERS, args.available_workers, args.parallel_scopes) if lane == "luna_wave" else (1 if lane == "luna_single" else 0),
        "reasons": reasons,
        "sol_final_acceptance": True,
    }


def command_route(args: argparse.Namespace) -> int:
    print(json.dumps(route(args), indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="subcommand", required=True)

    init = sub.add_parser("init", help="create an orchestration run")
    init.add_argument("run_dir")
    init.add_argument("--goal", required=True)
    init.add_argument("--acceptance", required=True)
    init.add_argument("--candidate-digest")
    init.set_defaults(func=command_init)

    packet = sub.add_parser("packet", help="create and validate a work packet")
    packet.add_argument("run_dir")
    packet.add_argument("--id", required=True)
    packet.add_argument("--agent", required=True)
    packet.add_argument("--role", required=True)
    packet.add_argument("--objective", required=True)
    packet.add_argument("--done-when", action="append", required=True)
    packet.add_argument("--owned-path", action="append", default=[])
    packet.add_argument("--do-not-touch", action="append", default=[])
    packet.add_argument("--input", action="append", default=[])
    packet.add_argument("--validation", action="append", required=True)
    packet.add_argument("--risk", choices=sorted(RISKS), default="low")
    packet.set_defaults(func=command_packet)

    receipt = sub.add_parser("receipt", help="create and validate an evidence receipt")
    receipt.add_argument("run_dir")
    receipt.add_argument("--packet-id", required=True)
    receipt.add_argument("--status", choices=sorted(STATUSES), required=True)
    receipt.add_argument("--summary", required=True)
    receipt.add_argument("--changed-file", action="append", default=[])
    receipt.add_argument("--command", action="append", default=[], help="COMMAND::EXIT_CODE")
    receipt.add_argument("--evidence", action="append", default=[], help="KIND:PATH")
    receipt.add_argument("--risk", action="append", default=[])
    receipt.add_argument("--candidate-digest", required=True)
    receipt.add_argument("--next-action", required=True)
    receipt.set_defaults(func=command_receipt)

    validate = sub.add_parser("validate", help="validate all run contracts")
    validate.add_argument("run_dir")
    validate.set_defaults(func=command_validate)

    summary = sub.add_parser("summary", help="print a compact run summary")
    summary.add_argument("run_dir")
    summary.set_defaults(func=command_summary)

    route_parser = sub.add_parser("route", help="recommend the cheapest safe lane")
    route_parser.add_argument("--ambiguity", choices=("low", "medium", "high"), default="low")
    route_parser.add_argument("--risk", choices=sorted(RISKS), default="low")
    route_parser.add_argument("--parallel-scopes", type=int, default=1)
    route_parser.add_argument("--available-workers", type=int, default=MAX_CONCURRENT_WORKERS,
                              help="live free slots, capped by the configured session limit")
    route_parser.add_argument("--ownership-disjoint", action="store_true")
    route_parser.add_argument("--cross-module", action="store_true")
    route_parser.add_argument("--tiny", action="store_true")
    route_parser.set_defaults(func=command_route)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "parallel_scopes", 1) < 1:
        parser.error("--parallel-scopes must be at least 1")
    if getattr(args, "available_workers", 0) < 0:
        parser.error("--available-workers cannot be negative")
    try:
        return args.func(args)
    except ContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
