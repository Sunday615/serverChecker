from __future__ import annotations

from typing import Any

from src.ssh_runner import SSHRunner
from src.utils import safe_string


def get_service_connection(service: dict[str, Any]) -> dict[str, Any]:
    connection = service.get("connection", {}) or {}

    return {
        "protocol": safe_string(connection.get("protocol") or "ssh").lower(),
        "ssh_port": int(connection.get("ssh_port") or 22),
        "username": safe_string(connection.get("username")),
        "password": safe_string(connection.get("password")),
    }


def _parse_stdout_int(stdout: str) -> int | None:
    text = (stdout or "").strip()
    if not text:
        return None

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None

    last_line = lines[-1]
    try:
        return int(last_line)
    except ValueError:
        return None


def evaluate_check_result(step: dict[str, Any], result: dict[str, Any]) -> tuple[bool, list[str]]:
    ok = bool(result["ok"])
    notes: list[str] = []

    stdout = result.get("stdout", "") or ""
    stderr = result.get("stderr", "") or ""

    for pattern in step.get("expect_stdout_contains", []) or []:
        if pattern not in stdout:
            ok = False
            notes.append(f"Missing expected stdout text: {pattern}")

    for pattern in step.get("expect_stderr_contains", []) or []:
        if pattern not in stderr:
            ok = False
            notes.append(f"Missing expected stderr text: {pattern}")

    for pattern in step.get("fail_if_stdout_contains", []) or []:
        if pattern in stdout:
            ok = False
            notes.append(f"Forbidden stdout text found: {pattern}")

    for pattern in step.get("fail_if_stderr_contains", []) or []:
        if pattern in stderr:
            ok = False
            notes.append(f"Forbidden stderr text found: {pattern}")

    if "expect_stdout_int_gte" in step:
        value = _parse_stdout_int(stdout)
        expected = int(step["expect_stdout_int_gte"])
        if value is None:
            ok = False
            notes.append("Failed to parse stdout integer for expect_stdout_int_gte")
        elif value < expected:
            ok = False
            notes.append(f"Parsed stdout integer {value} is lower than expected minimum {expected}")

    if "expect_stdout_int_eq" in step:
        value = _parse_stdout_int(stdout)
        expected = int(step["expect_stdout_int_eq"])
        if value is None:
            ok = False
            notes.append("Failed to parse stdout integer for expect_stdout_int_eq")
        elif value != expected:
            ok = False
            notes.append(f"Parsed stdout integer {value} is not equal to expected {expected}")

    return ok, notes


def _normalize_text_lines(text: str) -> list[str]:
    if text == "":
        return []

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.rstrip("\n")
    return normalized.split("\n")


def build_terminal_transcript(
    prompt_host: str,
    username: str,
    terminal_entries: list[dict[str, Any]],
    connection_error: str = "",
) -> str:
    lines: list[str] = []

    if connection_error:
        lines.append(f"[{username}@{prompt_host} ~]$ connection failed")
        lines.extend(_normalize_text_lines(connection_error))
        return "\n".join(lines)

    for entry in terminal_entries:
        prompt_dir = safe_string(entry.get("prompt_dir") or "~")
        display_command = safe_string(entry.get("display_command") or entry.get("command") or "")
        lines.append(f"[{username}@{prompt_host} {prompt_dir}]$ {display_command}")

        stdout = entry.get("stdout", "") or ""
        stderr = entry.get("stderr", "") or ""

        if stdout:
            lines.extend(_normalize_text_lines(stdout))

        if stderr:
            lines.extend(_normalize_text_lines(stderr))

    return "\n".join(lines)


def build_config_error_result(
    host_item: dict[str, Any],
    service: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    host = safe_string(host_item.get("host"))
    display_name = safe_string(host_item.get("display_name") or host)
    prompt_host = safe_string(service.get("prompt_host") or host_item.get("prompt_host") or display_name or host)
    site = safe_string(host_item.get("site") or "")
    service_name = safe_string(service.get("name"))

    connection = get_service_connection(service)
    protocol = connection["protocol"]
    ssh_port = connection["ssh_port"]
    username = connection["username"]

    terminal_entries: list[dict[str, Any]] = []
    raw_log = build_terminal_transcript(
        prompt_host=prompt_host,
        username=username or "unknown",
        terminal_entries=terminal_entries,
        connection_error=message,
    )

    return {
        "host": host,
        "display_name": display_name,
        "prompt_host": prompt_host,
        "site": site,
        "service_name": service_name,
        "username": username,
        "protocol": protocol,
        "ssh_port": ssh_port,
        "profile_name": safe_string(service.get("check_profile")),
        "status": "CONFIG_ERROR",
        "passed": 0,
        "failed": 1,
        "checks": [],
        "terminal_entries": terminal_entries,
        "raw_log": raw_log,
        "connection_error": message,
    }


def execute_host_service_checks(
    host_item: dict[str, Any],
    service: dict[str, Any],
    profile: dict[str, Any],
    default_timeout_sec: int,
) -> dict[str, Any]:
    host = safe_string(host_item.get("host"))
    display_name = safe_string(host_item.get("display_name") or host)
    prompt_host = safe_string(service.get("prompt_host") or host_item.get("prompt_host") or display_name or host)
    site = safe_string(host_item.get("site") or "")
    service_name = safe_string(service.get("name"))
    profile_name = safe_string(service.get("check_profile"))

    connection = get_service_connection(service)
    protocol = connection["protocol"]
    ssh_port = connection["ssh_port"]
    username = connection["username"]
    password = connection["password"]

    if protocol != "ssh":
        return build_config_error_result(
            host_item=host_item,
            service=service,
            message=f"Unsupported protocol: {protocol}",
        )

    if not username:
        return build_config_error_result(
            host_item=host_item,
            service=service,
            message="Missing username in service connection config",
        )

    check_steps = profile.get("checks", []) or []
    if not check_steps:
        return build_config_error_result(
            host_item=host_item,
            service=service,
            message=f"Profile '{profile_name}' has no checks configured",
        )

    runner = SSHRunner(
        host=host,
        username=username,
        password=password,
        ssh_port=ssh_port,
        connect_timeout=10,
    )

    checks_result: list[dict[str, Any]] = []
    terminal_entries: list[dict[str, Any]] = []
    connection_error = ""

    try:
        runner.open()
    except Exception as exc:
        connection_error = str(exc)
        raw_log = build_terminal_transcript(
            prompt_host=prompt_host,
            username=username,
            terminal_entries=terminal_entries,
            connection_error=connection_error,
        )
        return {
            "host": host,
            "display_name": display_name,
            "prompt_host": prompt_host,
            "site": site,
            "service_name": service_name,
            "username": username,
            "protocol": protocol,
            "ssh_port": ssh_port,
            "profile_name": profile_name,
            "status": "CONNECTION_FAILED",
            "passed": 0,
            "failed": 1,
            "checks": [],
            "terminal_entries": terminal_entries,
            "raw_log": raw_log,
            "connection_error": connection_error,
        }

    try:
        for step in check_steps:
            display_command = safe_string(step.get("display_command") or step.get("command") or "")
            prompt_dir = safe_string(step.get("prompt_dir") or "~")
            display_only = bool(step.get("display_only", False))

            if display_only:
                terminal_entries.append(
                    {
                        "prompt_dir": prompt_dir,
                        "display_command": display_command,
                        "stdout": "",
                        "stderr": "",
                    }
                )
                continue

            timeout = int(step.get("timeout", default_timeout_sec))
            pty = bool(step.get("pty", step.get("requires_pty", False)))
            wrap_in_bash = bool(step.get("wrap_in_bash", True))
            command = safe_string(step.get("command"))

            run_result = runner.run(
                name=step["name"],
                command=command,
                timeout=timeout,
                pty=pty,
                wrap_in_bash=wrap_in_bash,
            )

            current = {
                "name": run_result.name,
                "command": command,
                "display_command": display_command,
                "prompt_dir": prompt_dir,
                "ok": run_result.ok,
                "exit_code": run_result.exit_code,
                "stdout": run_result.stdout,
                "stderr": run_result.stderr,
                "duration_sec": run_result.duration_sec,
                "error": run_result.error,
                "notes": [],
            }

            final_ok, notes = evaluate_check_result(step, current)

            runner_notes: list[str] = []
            if run_result.error:
                runner_notes.append(f"Runner error: {run_result.error}")

            current["ok"] = final_ok
            current["notes"] = runner_notes + notes

            checks_result.append(current)
            terminal_entries.append(
                {
                    "prompt_dir": prompt_dir,
                    "display_command": display_command,
                    "stdout": run_result.stdout,
                    "stderr": run_result.stderr,
                }
            )
    finally:
        runner.close()

    passed = sum(1 for item in checks_result if item["ok"])
    failed = sum(1 for item in checks_result if not item["ok"])
    status = "PASS" if failed == 0 else "FAIL"

    raw_log = build_terminal_transcript(
        prompt_host=prompt_host,
        username=username,
        terminal_entries=terminal_entries,
        connection_error="",
    )

    return {
        "host": host,
        "display_name": display_name,
        "prompt_host": prompt_host,
        "site": site,
        "service_name": service_name,
        "username": username,
        "protocol": protocol,
        "ssh_port": ssh_port,
        "profile_name": profile_name,
        "status": status,
        "passed": passed,
        "failed": failed,
        "checks": checks_result,
        "terminal_entries": terminal_entries,
        "raw_log": raw_log,
        "connection_error": "",
    }