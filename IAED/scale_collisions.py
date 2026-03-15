#!/usr/bin/env python3
import argparse
import subprocess
import tempfile
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


def find_colliding_eans(start: int, count: int, max_tries: int) -> tuple[list[str], int, int]:
    first = ean8_from_base(start)
    target = hash_fnv1a_c_style(first) % HASH_SIZE
    out = [first]
    tries = 1
    n = start + 1

    while len(out) < count and tries < max_tries:
        if n > 9_999_999:
            n = 0
        ean = ean8_from_base(n)
        if hash_fnv1a_c_style(ean) % HASH_SIZE == target:
            out.append(ean)
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Hash-collision stress with valid EAN-8 keys.")
    parser.add_argument("--exe", default="../proj", help="Path to executable under test.")
    parser.add_argument("--count", type=int, default=200, help="How many colliding EANs to generate.")
    parser.add_argument("--start", type=int, default=1000000, help="Starting 7-digit base for EAN-8 generation.")
    parser.add_argument("--max-tries", type=int, default=20000000, help="Max candidates to scan for collisions.")
    parser.add_argument("--timeout", type=int, default=120, help="Execution timeout in seconds.")
    args = parser.parse_args()

    exe = Path(args.exe)
    if not exe.exists():
        print(f"Executable not found: {exe}")
        return 2
    if args.count < 1:
        print("count must be >= 1")
        return 2

    eans, bucket, tries = find_colliding_eans(args.start, args.count, args.max_tries)
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
        with in_path.open("rb") as fin, out_path.open("wb") as fout:
            proc = subprocess.run(
                [str(exe)],
                stdin=fin,
                stdout=fout,
                stderr=subprocess.PIPE,
                timeout=args.timeout,
            )
        if proc.returncode != 0:
            print(f"Program exited with code {proc.returncode}")
            if proc.stderr:
                print(proc.stderr.decode("utf-8", errors="replace"))
            return 1

        actual = out_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if actual != expected:
            print("Collision test FAILED: output mismatch.")
            print(f"Bucket={bucket}, collisions={len(eans)}, tries={tries}")
            print(f"Input file: {in_path}")
            print(f"Output file: {out_path}")
            exp_path = td_path / "collisions.expected"
            exp_path.write_text("\n".join(expected) + "\n", encoding="utf-8")
            print(f"Expected file: {exp_path}")
            return 1

    print(f"Collision test passed: bucket={bucket}, collisions={len(eans)}, tries={tries}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
