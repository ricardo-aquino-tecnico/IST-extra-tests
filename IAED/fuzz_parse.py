#!/usr/bin/env python3
import argparse
import random
import string
import subprocess
from pathlib import Path


def rand_word(rng: random.Random, min_len: int, max_len: int) -> str:
    letters = string.ascii_letters + string.digits + "_-*/?\"' \t"
    n = rng.randint(min_len, max_len)
    return "".join(rng.choice(letters) for _ in range(n))


def maybe_quote(rng: random.Random, s: str) -> str:
    mode = rng.randrange(4)
    if mode == 0:
        return s
    if mode == 1:
        return f"\"{s}\""
    if mode == 2:
        return f"\"{s}"
    return f"{s}\""


def make_line(rng: random.Random) -> str:
    kind = rng.randrange(12)
    if kind == 0:
        return "p " + rand_word(rng, 0, 40)
    if kind == 1:
        return "a " + rand_word(rng, 0, 20)
    if kind == 2:
        return "f " + maybe_quote(rng, rand_word(rng, 0, 40))
    if kind == 3:
        return "c " + maybe_quote(rng, rand_word(rng, 0, 40))
    if kind == 4:
        return "d " + rand_word(rng, 0, 20)
    if kind == 5:
        return "r " + rand_word(rng, 0, 20)
    if kind == 6:
        return "l " + rand_word(rng, 0, 20)
    if kind == 7:
        return rand_word(rng, 0, 80)
    if kind == 8:
        return "x " + rand_word(rng, 0, 30)
    if kind == 9:
        return " " * rng.randint(0, 40)
    if kind == 10:
        return "\t" * rng.randint(0, 20) + "f " + rand_word(rng, 0, 30)
    return "p " + rand_word(rng, 10, 120)


def run_case(exe: Path, seed: int, case_id: int, max_lines: int, timeout_s: int, fail_dir: Path) -> bool:
    rng = random.Random(seed + case_id * 10007)
    n_lines = rng.randint(1, max_lines)
    lines = [make_line(rng) for _ in range(n_lines)]
    lines.append("q")
    input_text = "\n".join(lines) + "\n"

    try:
        proc = subprocess.run(
            [str(exe)],
            input=input_text.encode("utf-8", errors="ignore"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        fail_dir.mkdir(parents=True, exist_ok=True)
        base = fail_dir / f"fuzz_seed_{seed}_case_{case_id}"
        base.with_suffix(".in").write_text(input_text, encoding="utf-8", errors="ignore")
        base.with_suffix(".reason").write_text("timeout", encoding="utf-8")
        return False

    if proc.returncode == 0:
        return True

    fail_dir.mkdir(parents=True, exist_ok=True)
    base = fail_dir / f"fuzz_seed_{seed}_case_{case_id}"
    base.with_suffix(".in").write_text(input_text, encoding="utf-8", errors="ignore")
    base.with_suffix(".stdout").write_text(proc.stdout.decode("utf-8", errors="replace"), encoding="utf-8")
    base.with_suffix(".stderr").write_text(proc.stderr.decode("utf-8", errors="replace"), encoding="utf-8")
    base.with_suffix(".reason").write_text(f"exit_code={proc.returncode}", encoding="utf-8")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Crash-oriented parser fuzzer for proj.")
    parser.add_argument("--exe", default="../proj", help="Path to executable under test.")
    parser.add_argument("--cases", type=int, default=400, help="Number of random programs to run.")
    parser.add_argument("--max-lines", type=int, default=300, help="Max random lines per case (without final q).")
    parser.add_argument("--seed", type=int, default=260315, help="Base RNG seed.")
    parser.add_argument("--timeout", type=int, default=5, help="Timeout in seconds per case.")
    parser.add_argument("--fail-dir", default="fuzz-failures", help="Where to write failing cases.")
    args = parser.parse_args()

    exe = Path(args.exe)
    if not exe.exists():
        print(f"Executable not found: {exe}")
        return 2

    fail_dir = Path(args.fail_dir)
    for i in range(args.cases):
        ok = run_case(exe, args.seed, i, args.max_lines, args.timeout, fail_dir)
        if not ok:
            print(f"Fuzz failure at case {i} (seed={args.seed}). See {fail_dir}.")
            return 1
        if (i + 1) % 50 == 0:
            print(f"passed {i + 1}/{args.cases} fuzz cases")

    print(f"Fuzz parse passed: cases={args.cases}, max_lines={args.max_lines}, seed={args.seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
