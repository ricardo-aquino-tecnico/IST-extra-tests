#!/usr/bin/env python3
import argparse
import random
import string
import subprocess
from pathlib import Path


def rand_word(rng: random.Random, min_len: int, max_len: int) -> str:
    letters = string.ascii_letters + string.digits + "_-*/?"
    n = rng.randint(min_len, max_len)
    return "".join(rng.choice(letters) for _ in range(n))


def make_valid_ean(rng: random.Random, length: int) -> str:
    body = "".join(rng.choice(string.digits) for _ in range(length - 1))
    s = 0
    for i, ch in enumerate(body):
        d = ord(ch) - ord("0")
        s += d if i % 2 == 0 else d * 3
    check = (10 - (s % 10)) % 10
    return body + str(check)


def make_ean_token(rng: random.Random) -> str:
    kind = rng.randrange(4)
    if kind == 0:
        return make_valid_ean(rng, rng.choice([8, 13]))
    if kind == 1:
        e = make_valid_ean(rng, rng.choice([8, 13]))
        bad = (int(e[-1]) + rng.randint(1, 9)) % 10
        return e[:-1] + str(bad)
    if kind == 2:
        return "".join(rng.choice(string.digits) for _ in range(rng.choice([1, 2, 7, 9, 12])))
    return "".join(rng.choice(string.digits) for _ in range(rng.choice([8, 13])))


def make_name(rng: random.Random) -> str:
    return rng.choice(
        [
            "Ana",
            "Rui",
            "Bruno",
            "joao",
            "maria",
            "Cliente",
            "Cliente final",
            "Ana Maria",
            "8ball",
            "_rui",
        ]
    )


def format_name_arg(rng: random.Random, name: str) -> str:
    if " " in name or "\t" in name:
        mode = rng.randrange(3)
        if mode == 0:
            return f"\"{name}\""
        if mode == 1:
            return f"\"{name}"
        return name
    return name


def make_line(rng: random.Random) -> str:
    kind = rng.randrange(10)
    if kind == 0:
        ean = make_ean_token(rng)
        iva = rng.choice(["A", "B", "C", "D", "E", "x"])
        price = rng.choice(
            [
                f"{rng.randint(1, 20000) / 100:.2f}",
                "0.00",
                "-1.00",
                f"{rng.randint(1, 20000)}",
            ]
        )
        qty = str(rng.choice([-20, -1, 0, 1, 2, 5, 10, 30, 2147483648]))
        desc_head = rng.choice(string.ascii_letters + string.digits)
        desc_tail = rand_word(rng, 0, 20)
        desc = (desc_head + desc_tail).strip() or "A"
        return f"p {ean} {iva} {price} {qty} {desc}"
    if kind == 1:
        sub = rng.randrange(3)
        if sub == 0:
            return "a"
        ean = make_ean_token(rng)
        if sub == 1:
            return f"a {ean}"
        qty = rng.choice([-15, -5, -1, 0, 1, 2, 3, 10, 20, 21474836480])
        return f"a {qty} {ean}"
    if kind == 2:
        sub = rng.randrange(5)
        if sub == 0:
            return "f"
        if sub == 1:
            return f"f {format_name_arg(rng, make_name(rng))}"
        if sub == 2:
            nif = "".join(rng.choice(string.digits) for _ in range(rng.choice([8, 9, 10])))
            return f"f {nif} {format_name_arg(rng, make_name(rng))}"
        if sub == 3:
            return f'f "{make_name(rng)}'
        return f"f {rand_word(rng, 1, 12)}"
    if kind == 3:
        sub = rng.randrange(4)
        if sub == 0:
            return "c"
        if sub == 1:
            return f"c {format_name_arg(rng, make_name(rng))}"
        if sub == 2:
            return f'c "{make_name(rng)}'
        return f"c {rand_word(rng, 1, 16)}"
    if kind == 4:
        if rng.random() < 0.5:
            inv = rng.choice([-2, -1, 0, 1, 2, 10, 9999999999])
            return f"d {inv}"
        return f"d {make_ean_token(rng)} {rng.choice([-10, -1, 0, 1, 2, 5, 30, 21474836480])}"
    if kind == 5:
        if rng.random() < 0.5:
            return "r"
        return f"r {make_ean_token(rng)}"
    if kind == 6:
        if rng.random() < 0.4:
            return "l"
        pats = []
        for _ in range(rng.randint(1, 3)):
            pats.append(rng.choice(["*", "999*", "?" * 8, "?" * 13, make_ean_token(rng)]))
        return "l " + " ".join(pats)
    if kind == 7:
        return " " * rng.randint(0, 30)
    if kind == 8:
        return "\t" * rng.randint(0, 10) + "a"
    return rng.choice(["q", "p", "l", "a", "r", "f", "c", "d"])


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
    except subprocess.TimeoutExpired as exc:
        fail_dir.mkdir(parents=True, exist_ok=True)
        base = fail_dir / f"fuzz_seed_{seed}_case_{case_id}"
        base.with_suffix(".in").write_text(input_text, encoding="utf-8", errors="ignore")
        base.with_suffix(".out").write_text(
            (exc.stdout or b"").decode("utf-8", errors="replace"),
            encoding="utf-8",
        )
        base.with_suffix(".stderr").write_text(
            (exc.stderr or b"").decode("utf-8", errors="replace"),
            encoding="utf-8",
        )
        base.with_suffix(".reason").write_text(f"timeout after {timeout_s}s", encoding="utf-8")
        return False

    if proc.returncode == 0:
        return True

    fail_dir.mkdir(parents=True, exist_ok=True)
    base = fail_dir / f"fuzz_seed_{seed}_case_{case_id}"
    base.with_suffix(".in").write_text(input_text, encoding="utf-8", errors="ignore")
    base.with_suffix(".out").write_text(proc.stdout.decode("utf-8", errors="replace"), encoding="utf-8")
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
    parser.add_argument(
        "--progress-every",
        type=int,
        default=50,
        help="Print progress every N cases (0 disables progress).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable intermediate progress messages.",
    )
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
        if not args.quiet and args.progress_every > 0 and (i + 1) % args.progress_every == 0:
            print(f"passed {i + 1}/{args.cases} fuzz cases")

    print(f"Fuzz parse passed: cases={args.cases}, max_lines={args.max_lines}, seed={args.seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
