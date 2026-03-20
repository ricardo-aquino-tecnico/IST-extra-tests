#!/usr/bin/env python3
import argparse
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path


HASH_SIZE = 20011
MASK64 = (1 << 64) - 1


def hash_fnv1a_c_style(s: str) -> int:
    h = 2166136261
    for b in s.encode("ascii"):
        h ^= b
        h = (h * 16777619) & MASK64
    return h


def ean8_from_base(n: int) -> str:
    base = f"{n:07d}"
    s = 0
    for i, ch in enumerate(base):
        d = ord(ch) - 48
        s += d if i % 2 == 0 else d * 3
    cd = (10 - (s % 10)) % 10
    return base + str(cd)


def find_colliding_eans(
    start: int, count: int, max_tries: int, progress_every: int, quiet: bool
) -> tuple[list[str], int, int]:
    first = ean8_from_base(start)
    target = hash_fnv1a_c_style(first) % HASH_SIZE
    out = [first]
    tries = 1
    n = start + 1

    if not quiet:
        print(
            f"Collision search started: target_bucket={target}, "
            f"goal={count}, max_tries={max_tries}",
            flush=True,
        )

    while len(out) < count and tries < max_tries:
        if n > 9_999_999:
            n = 0
        ean = ean8_from_base(n)
        if hash_fnv1a_c_style(ean) % HASH_SIZE == target:
            out.append(ean)
        if not quiet and progress_every > 0 and tries % progress_every == 0:
            print(
                f"Collision search progress: tries={tries}, found={len(out)}/{count}",
                flush=True,
            )
        tries += 1
        n += 1

    return out, target, tries


def build_case(path: Path, eans: list[str]) -> list[str]:
    expected: list[str] = []
    with path.open("w", encoding="utf-8") as f:
        for i, ean in enumerate(eans):
            f.write(f"p {ean} A 1.00 2 P{i}\n")
            expected.append("2")

        for i, ean in enumerate(eans):
            f.write(f"a {ean}\n")
            f.write(f"r {ean}\n")
            f.write(f"a -1 {ean}\n")
            f.write(f"r {ean}\n")
            expected.append(f"A 1.00 1 1.00 P{i}")
            expected.append(f"1 1 P{i}")
            expected.append(f"A 1.00 0 0.00 P{i}")
            expected.append(f"2 0 P{i}")

        f.write("l ????????\n")
        for i, ean in enumerate(eans):
            expected.append(f"{ean} A 1.00 0 2 P{i}")
        f.write("q\n")
    return expected


def dump_failure_artifacts(
    fail_dir: Path,
    prefix: str,
    in_path: Path,
    out_path: Path,
    stderr_data: bytes,
    reason: str,
    expected_lines: list[str] | None = None,
) -> Path:
    fail_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    base = fail_dir / f"{prefix}_{stamp}"

    if in_path.exists():
        base.with_suffix(".in").write_bytes(in_path.read_bytes())
    if out_path.exists():
        base.with_suffix(".out").write_bytes(out_path.read_bytes())
    base.with_suffix(".stderr").write_bytes(stderr_data or b"")
    if expected_lines is not None:
        base.with_suffix(".expected").write_text("\n".join(expected_lines) + "\n", encoding="utf-8")
    base.with_suffix(".reason").write_text(reason + "\n", encoding="utf-8")
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description="Hash-collision stress with valid EAN-8 keys.")
    parser.add_argument("--exe", default="../proj", help="Path to executable under test.")
    parser.add_argument("--count", type=int, default=200, help="How many colliding EANs to generate.")
    parser.add_argument("--start", type=int, default=1000000, help="Starting 7-digit base for EAN-8 generation.")
    parser.add_argument("--max-tries", type=int, default=20000000, help="Max candidates to scan for collisions.")
    parser.add_argument(
        "--progress-every",
        type=int,
        default=500000,
        help="Print search progress every N candidates (0 disables progress).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable intermediate progress messages.",
    )
    parser.add_argument("--timeout", type=int, default=120, help="Execution timeout in seconds.")
    parser.add_argument("--fail-dir", default="collisions-failures", help="Where to persist failure artifacts.")
    args = parser.parse_args()

    exe = Path(args.exe)
    if not exe.exists():
        print(f"Executable not found: {exe}")
        return 2
    if args.count < 1:
        print("count must be >= 1")
        return 2

    fail_dir = Path(args.fail_dir)
    eans, bucket, tries = find_colliding_eans(
        args.start, args.count, args.max_tries, args.progress_every, args.quiet
    )
    if len(eans) < args.count:
        print(
            f"Could not find {args.count} collisions for one bucket within {args.max_tries} tries "
            f"(found {len(eans)})."
        )
        return 1

    with tempfile.TemporaryDirectory(prefix="collisions_") as td:
        td_path = Path(td)
        in_path = td_path / "collisions.in"
        out_path = td_path / "collisions.out"

        expected = build_case(in_path, eans)
        try:
            with in_path.open("rb") as fin, out_path.open("wb") as fout:
                proc = subprocess.run(
                    [str(exe)],
                    stdin=fin,
                    stdout=fout,
                    stderr=subprocess.PIPE,
                    timeout=args.timeout,
                )
        except subprocess.TimeoutExpired as exc:
            reason = f"timeout after {args.timeout}s; bucket={bucket}, collisions={len(eans)}, tries={tries}"
            base = dump_failure_artifacts(
                fail_dir,
                "collisions",
                in_path,
                out_path,
                exc.stderr or b"",
                reason,
                expected_lines=expected,
            )
            print(f"Collision test FAILED: {reason}")
            print(f"Failure artifacts: {base}.*")
            return 1

        if proc.returncode != 0:
            reason = f"exit_code={proc.returncode}; bucket={bucket}, collisions={len(eans)}, tries={tries}"
            base = dump_failure_artifacts(
                fail_dir,
                "collisions",
                in_path,
                out_path,
                proc.stderr,
                reason,
                expected_lines=expected,
            )
            print(f"Program exited with code {proc.returncode}")
            if proc.stderr:
                print(proc.stderr.decode("utf-8", errors="replace"))
            print(f"Failure artifacts: {base}.*")
            return 1

        actual = out_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if actual != expected:
            reason = f"output mismatch; bucket={bucket}, collisions={len(eans)}, tries={tries}"
            base = dump_failure_artifacts(
                fail_dir,
                "collisions",
                in_path,
                out_path,
                proc.stderr,
                reason,
                expected_lines=expected,
            )
            print("Collision test FAILED: output mismatch.")
            print(f"Bucket={bucket}, collisions={len(eans)}, tries={tries}")
            print(f"Failure artifacts: {base}.*")
            return 1

    print(f"Collision test passed: bucket={bucket}, collisions={len(eans)}, tries={tries}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
