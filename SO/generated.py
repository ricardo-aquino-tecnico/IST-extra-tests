"""Geração reprodutível de stress, escala, fuzzing e identificadores semelhantes."""

import argparse
import json
import math
import os
from pathlib import Path
import random
import shutil
import tempfile
import time

from model import Model
from run_tests import ROOT, colour, run_case, save_result


FAIL_DIRS = ("stress-failures", "scale-failures", "fuzz-failures", "collisions-failures")


class Case:
    def __init__(self, model=None):
        self.model = model or Model()
        self.files = []
        self.expected = ""

    def file(self, text):
        self.files.append(text)

    def define(self, name, ram=1, disk=1, cpu=1, folder="@INPUT@"):
        self.model.define(name, ram, disk, cpu, folder)
        self.file(f"D {name} {folder} @EXE@ {ram} {disk} {cpu}\n")

    def reserve(self, rid, requests):
        self.model.reserve(rid, requests)
        self.file(f"R {rid} " + " ".join(f"{name} {count} {server}" for name, count, server in requests) + "\n")

    def snapshot(self):
        self.file("L\n")
        self.expected += self.model.listing()

    def copy(self, rid):
        self.file(f"A {rid}\n")
        number = 0
        for name, amount, _ in self.model.reservations[rid]:
            source = self.model.types[name][3]
            for _ in range(amount):
                number += 1
                relative = f"{rid}/{rid}_{number}"
                self.files[-1] += f"# COPY: {source} -> {relative}\n"
                self.expected += f"COPY {relative} OK\n"

    def write(self, base, description):
        base.with_suffix(".in").write_text("".join(f"# FILE: {i:08d}.conf\n{text}" for i, text in enumerate(self.files)))
        base.with_suffix(".out").write_text(self.expected)
        base.with_suffix(".arg").write_text(" ".join(map(str, self.model.args)) + "\n")
        base.with_suffix(".txt").write_text(description + "\n")


def stress_case(seed, steps):
    rng = random.Random(seed)
    case = Case()
    for step in range(steps):
        action = rng.randrange(6)
        if not case.model.types or action == 0 and len(case.model.types) < 8:
            case.define(f"TYPE{len(case.model.types):03d}", rng.randint(1, 3), rng.randint(1, 5), rng.choice((0.25, 0.5, 1)),
                        rng.choice(("@INPUT@", "@EMPTY@")))
        elif action in (1, 2) and len(case.model.reservations) < 16:
            requests = [(rng.choice(list(case.model.types)), rng.randint(1, 3), rng.randint(1, 4))]
            if rng.randrange(2):
                requests.append((rng.choice(list(case.model.types)), 1, rng.randint(1, 4)))
            case.reserve(f"@RESERV{len(case.model.reservations):06d}@", requests)
        elif action == 3:
            case.file("# Comentário aleatório\n\nE 0\n")
        else:
            case.snapshot()
    case.snapshot()
    for rid in list(case.model.reservations)[:2]:
        case.copy(rid)
    return case


def scale_case(types, files):
    case = Case()
    for i in range(types):
        case.define(f"TYPE{i:03d}", 1 + i % 3, 1 + i % 5, (1 + i % 4) / 4)
    for i in range(files):
        case.reserve(f"@RESERV{i:06d}@", [(f"TYPE{i % types:03d}", 1, i % 4 + 1)])
    case.snapshot()
    case.copy("@RESERV000000@")
    return case


def collision_case(count, start):
    case = Case()
    names = [("V" if i % 2 else "v") + "x" * 28 + f"{start+i:010d}" for i in range(count)]
    for i, name in enumerate(names):
        case.define(name, 1 + i % 3, 1 + i % 5, (1 + i % 4) / 4)
    for i in reversed(range(count)):
        case.reserve(f"@RESERV{i:06d}@", [(names[i], 1, i % 4 + 1)])
    case.snapshot()
    return case


def fuzz_case(seed, max_lines):
    rng = random.Random(seed)
    case = Case()
    case.file("# ROBUSTNESS\nD SAFE @INPUT@ @EXE@ 1 1 1\n")
    long_word = "x" * rng.randint(40, 180)
    noise = ["", "# comentário", "?", "UNKNOWN", "D", "R", "A", "E", "L extra", "H extra",
             "E -1", "E nan", "E 0 trailing", "E 18446744073709551616", "D " + long_word,
             "D SAFE @INPUT@ @EXE@ -1 1 1", "D BAD @INPUT@ @EXE@ 1 1 nan",
             "R @RESERV000000@ SAFE 0 1", "R @RESERV000000@ SAFE 1 0", "A UNKNOWN", "\tL", " L"]
    case.file("\n".join(rng.choice(noise) for _ in range(rng.randint(1, max_lines))) + "\n")
    return case


def parser_for(mode):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", required=True)
    parser.add_argument("--timeout", type=float, default=8)
    parser.add_argument("--seed", type=int, default=260315)
    parser.add_argument("--fail-dir", default={"stress": FAIL_DIRS[0], "scale": FAIL_DIRS[1], "fuzz": FAIL_DIRS[2], "collisions": FAIL_DIRS[3]}[mode])
    parser.add_argument("--progress-every", type=int, default=25)
    parser.add_argument("--quiet", action="store_true")
    if mode == "stress":
        parser.add_argument("--runs", type=int, default=200)
        parser.add_argument("--steps", type=int, default=250)
    elif mode == "scale":
        parser.add_argument("--types", "--products", dest="types", type=int, default=96)
        parser.add_argument("--files", "--invoices", dest="files", type=int, default=200)
    elif mode == "fuzz":
        parser.add_argument("--cases", type=int, default=400)
        parser.add_argument("--max-lines", type=int, default=300)
    else:
        parser.add_argument("--count", type=int, default=120)
        parser.add_argument("--start", type=int, default=1000000)
    return parser


def main(mode):
    parser = parser_for(mode)
    args = parser.parse_args()
    exe = Path(args.exe).expanduser().resolve()
    if not exe.is_file() or not os.access(exe, os.X_OK):
        parser.error(f"Executável inválido: {exe}")
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout deve ser positivo e finito")
    if mode == "scale" and not (1 <= args.types <= 128 and 1 <= args.files <= 256):
        parser.error("--types: 1..128; --files: 1..256 (limites do código base)")
    if mode == "collisions" and not (0 <= args.count <= 128 and 0 <= args.start and args.start + args.count <= 10**10):
        parser.error("--count: 0..128; --start deve permitir identificadores com até 39 caracteres")
    if mode == "stress" and (args.runs < 0 or args.steps < 1) or mode == "fuzz" and (args.cases < 0 or args.max_lines < 1):
        parser.error("Número de casos não negativo; linhas/passos positivos")
    total = args.runs if mode == "stress" else args.cases if mode == "fuzz" else int(args.count > 0) if mode == "collisions" else 1
    destination = Path(args.fail_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    failed = []
    passed = 0
    start = time.monotonic()
    print(f"{mode}: seed={args.seed}, casos={total}", flush=True)
    for i in range(total):
        seed = args.seed + i * 10007
        case = stress_case(seed, args.steps) if mode == "stress" else scale_case(args.types, args.files) if mode == "scale" else fuzz_case(seed, args.max_lines) if mode == "fuzz" else collision_case(args.count, args.start)
        name = f"seed_{args.seed}_case_{i:06d}"
        with tempfile.TemporaryDirectory(prefix="so-generated-") as temp:
            base = Path(temp) / name
            case.write(base, f"Suite {mode}; seed={args.seed}; caso={i}; parâmetros={vars(args)}")
            result = run_case(base.with_suffix(".in"), exe, args.timeout)
            if result["reasons"]:
                save_result(base.with_suffix(".in"), result)
                for path in base.parent.glob(name + ".*"):
                    shutil.copyfile(path, destination / path.name)
                failed.append(name + ".in")
                print(colour("FAIL " + name + ": " + "; ".join(result["reasons"]), "1;31"), flush=True)
                break
        passed += 1
        if not args.quiet and args.progress_every > 0 and passed % args.progress_every == 0:
            print(f"{passed}/{total} passaram", flush=True)
    (destination / "tests_failed.log").write_text("".join(name + "\n" for name in failed))
    metadata = {"suite": mode, "seed": args.seed, "planned": total, "passed": passed, "failed": len(failed),
                "elapsed": time.monotonic() - start, "parameters": vars(args)}
    (destination / "suite.status.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(colour(f"{mode}: {passed} passaram; {len(failed)} falharam; {total} previstos", "1;31" if failed else "1;32"), flush=True)
    return bool(failed)
