from __future__ import annotations

import time
from dataclasses import dataclass
from shlex import quote

from fabric import Connection


@dataclass
class SSHRunResult:
    name: str
    command: str
    ok: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_sec: float
    error: str = ""


class SSHRunner:
    def __init__(
        self,
        host: str,
        username: str,
        password: str = "",
        ssh_port: int = 22,
        connect_timeout: int = 10,
    ) -> None:
        connect_kwargs = {}

        if password:
            connect_kwargs["password"] = password
            connect_kwargs["allow_agent"] = False
            connect_kwargs["look_for_keys"] = False

        self.connection = Connection(
            host=host,
            user=username,
            port=ssh_port,
            connect_kwargs=connect_kwargs,
            connect_timeout=connect_timeout,
        )

    def open(self) -> None:
        self.connection.open()

    def close(self) -> None:
        self.connection.close()

    def _build_shell_command(self, command: str, wrap_in_bash: bool) -> str:
        stripped = (command or "").strip()

        if not stripped:
            return "true"

        if not wrap_in_bash:
            return stripped

        lowered = stripped.lower()
        if (
            lowered.startswith("bash -lc ")
            or lowered.startswith("bash -c ")
            or lowered.startswith("sh -lc ")
            or lowered.startswith("sh -c ")
        ):
            return stripped

        return f"bash -lc {quote(stripped)}"

    def _extract_streams_from_exception(self, exc: Exception) -> tuple[str, str, int]:
        result = getattr(exc, "result", None)

        stdout = getattr(result, "stdout", "") or ""
        stderr = getattr(result, "stderr", "") or ""
        exit_code = getattr(result, "exited", -1)

        try:
            exit_code = int(exit_code)
        except Exception:
            exit_code = -1

        return stdout, stderr, exit_code

    def run(
        self,
        name: str,
        command: str,
        timeout: int = 20,
        pty: bool = False,
        wrap_in_bash: bool = True,
    ) -> SSHRunResult:
        started_at = time.monotonic()
        shell_command = self._build_shell_command(command=command, wrap_in_bash=wrap_in_bash)

        try:
            result = self.connection.run(
                shell_command,
                hide=True,
                warn=True,
                timeout=timeout,
                pty=pty,
            )
            duration_sec = time.monotonic() - started_at

            return SSHRunResult(
                name=name,
                command=command,
                ok=bool(result.ok),
                exit_code=int(result.exited),
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                duration_sec=duration_sec,
                error="",
            )

        except Exception as exc:
            duration_sec = time.monotonic() - started_at
            stdout, stderr, exit_code = self._extract_streams_from_exception(exc)

            return SSHRunResult(
                name=name,
                command=command,
                ok=False,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_sec=duration_sec,
                error=str(exc),
            )