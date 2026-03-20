#!/usr/bin/env python3
import argparse
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path


MAX_PRODUCTS = 10000
TAX = {"A": 0, "B": 6, "C": 13, "D": 23}


@dataclass
class Product:
    ean: str
    iva: str
    price_cents: int
    quantity: int
    sold: int
    in_basket: int
    desc: str


@dataclass
class Invoice:
    inv_id: int
    nif: str
    name: str
    total_products: int
    total_value: int


def money(cents: int) -> str:
    return f"{cents / 100:.2f}"


def wildcard_match(pattern: str, text: str) -> bool:
    star = None
    ss = 0
    i = 0
    j = 0
    while j < len(text):
        if i < len(pattern) and (pattern[i] == "?" or pattern[i] == text[j]):
            i += 1
            j += 1
        elif i < len(pattern) and pattern[i] == "*":
            star = i
            i += 1
            ss = j
        elif star is not None:
            i = star + 1
            ss += 1
            j = ss
        else:
            return False
    while i < len(pattern) and pattern[i] == "*":
        i += 1
    return i == len(pattern)


def is_valid_ean(ean: str) -> bool:
    if len(ean) not in (8, 13):
        return False
    if not ean[:-1].isdigit() or not ean[-1].isdigit():
        return False
    s = 0
    for i, ch in enumerate(ean[:-1]):
        d = ord(ch) - ord("0")
        s += d if i % 2 == 0 else d * 3
    check = (10 - (s % 10)) % 10
    return (ord(ean[-1]) - ord("0")) == check


def starts_with_letter_desc(s: str) -> bool:
    return bool(s) and ("A" <= s[0] <= "Z")


def starts_with_letter_name(s: str) -> bool:
    return bool(s) and (("A" <= s[0] <= "Z") or ("a" <= s[0] <= "z"))


def valid_nif(nif: str) -> bool:
    return len(nif) == 9 and nif.isdigit()


class Model:
    def __init__(self) -> None:
        self.products = {}
        self.creation_order = []
        self.basket = {}
        self.invoices = []
        self.total_items_sold = 0
        self.invoice_count = 0
        self.total_billed = 0

    def search_product(self, ean: str):
        return self.products.get(ean)

    def cmd_p(self, ean: str, iva: str, price_cents: int, qty: int, desc: str):
        out = []
        p = self.search_product(ean)
        if not is_valid_ean(ean):
            return ["invalid ean"]
        if iva not in TAX:
            return ["invalid iva"]
        if price_cents <= 0:
            return ["invalid price"]
        if qty < 0:
            return ["invalid quantity"]
        if len(desc.encode("utf-8")) > 50 or not starts_with_letter_desc(desc):
            return ["invalid description"]
        if p is not None and p.in_basket > 0 and p.price_cents != price_cents:
            return ["product in use"]
        if p is None and len(self.products) >= MAX_PRODUCTS:
            return ["invalid product"]

        if p is None:
            p = Product(ean=ean, iva=iva, price_cents=price_cents, quantity=qty, sold=0, in_basket=0, desc=desc)
            self.products[ean] = p
            self.creation_order.append(ean)
        else:
            p.quantity += qty
            p.iva = iva
            p.price_cents = price_cents
            p.desc = desc
        out.append(str(p.quantity))
        return out

    def _basket_line(self, p: Product, qty: int) -> str:
        total = self._total_with_iva(p.price_cents, qty, p.iva)
        return f"{p.iva} {money(p.price_cents)} {qty} {money(total)} {p.desc}"

    @staticmethod
    def _total_with_iva(price_cents: int, qty: int, iva_code: str) -> int:
        # Mirror project.c floating-point path and symmetric cent rounding.
        base = (price_cents / 100.0) * qty
        taxed = base * (100.0 + TAX[iva_code]) / 100.0
        cents = taxed * 100.0
        if cents >= 0:
            return int(cents + 0.5 + 1e-12)
        return int(cents - 0.5 - 1e-12)

    def cmd_a_list(self):
        lines = []
        for ean in sorted(self.basket.keys()):
            qty = self.basket[ean]
            if qty > 0:
                lines.append(self._basket_line(self.products[ean], qty))
        return lines

    def cmd_a(self, ean: str, quantity: int):
        if not is_valid_ean(ean):
            return ["invalid ean"]
        p = self.search_product(ean)
        if p is None:
            return [f"{ean}: no such product"]
        cur = self.basket.get(ean, 0)
        if quantity < 0:
            if cur < -quantity:
                return ["invalid quantity"]
        elif quantity > 0:
            if p.quantity < quantity:
                return ["no stock"]
        p.quantity -= quantity
        p.in_basket += quantity
        new_qty = cur + quantity
        if new_qty == 0:
            self.basket.pop(ean, None)
        else:
            self.basket[ean] = new_qty
        return [self._basket_line(p, new_qty)]

    def cmd_f(self, nif: str, name: str):
        if nif != "999999999" and not valid_nif(nif):
            return [f"{nif}: no such nif"]
        if not starts_with_letter_name(name):
            return ["invalid name"]
        if name == "error":
            for ean, qty in list(self.basket.items()):
                p = self.products[ean]
                p.quantity += qty
                p.in_basket = 0
            self.basket.clear()
            return []
        items = 0
        total = 0
        for ean, qty in list(self.basket.items()):
            p = self.products[ean]
            total += self._total_with_iva(p.price_cents, qty, p.iva)
            items += qty
            p.sold += qty
            p.in_basket = 0
        self.basket.clear()
        self.invoice_count += 1
        self.total_items_sold += items
        self.total_billed += total
        self.invoices.append(
            Invoice(inv_id=self.invoice_count, nif=nif, name=name, total_products=items, total_value=total)
        )
        return [f"{items} {money(total)} {self.invoice_count}"]

    def cmd_d_invoice(self, inv_id: int):
        idx = -1
        for i, inv in enumerate(self.invoices):
            if inv.inv_id == inv_id:
                idx = i
                break
        if idx == -1:
            return [f"{inv_id}: no such invoice"]
        inv = self.invoices.pop(idx)
        self.total_items_sold -= inv.total_products
        self.total_billed -= inv.total_value
        return [f"{money(inv.total_value)} {inv.nif} {inv.name}"]

    def cmd_d_product(self, ean: str, qty: int):
        if not is_valid_ean(ean):
            return ["invalid ean"]
        p = self.search_product(ean)
        if p is None:
            return [f"{ean}: no such product"]
        if p.in_basket > 0:
            return ["product in use"]
        if qty <= 0 or qty > p.quantity:
            return ["invalid quantity"]
        p.quantity -= qty
        out = [f"{p.quantity} {p.desc}"]
        if p.quantity == 0:
            self.products.pop(ean)
            self.creation_order = [x for x in self.creation_order if x != ean]
            self.basket.pop(ean, None)
        return out

    def cmd_r(self, ean: str | None):
        if ean is None:
            lines = [f"{self.total_items_sold} {self.invoice_count} {money(self.total_billed)}"]
            for k in sorted(TAX.keys()):
                lines.append(f"{k} {TAX[k]}%")
            return lines
        if not is_valid_ean(ean):
            return ["invalid ean"]
        p = self.search_product(ean)
        if p is None:
            return [f"{ean}: no such product"]
        return [f"{p.quantity} {p.sold + p.in_basket} {p.desc}"]

    def cmd_l(self, patterns: list[str] | None):
        lines = []
        if not patterns:
            for ean in self.creation_order:
                p = self.products[ean]
                if p.quantity > 0:
                    lines.append(f"{ean} {p.iva} {money(p.price_cents)} {p.sold + p.in_basket} {p.quantity} {p.desc}")
            if not lines:
                lines.append("*: no such product")
            return lines
        for pat in patterns:
            found = False
            for ean in self.creation_order:
                p = self.products[ean]
                if p.quantity > 0 and wildcard_match(pat, ean):
                    lines.append(f"{ean} {p.iva} {money(p.price_cents)} {p.sold + p.in_basket} {p.quantity} {p.desc}")
                    found = True
            if not found:
                lines.append(f"{pat}: no such product")
        return lines

    def cmd_c(self, name: str | None):
        if name is not None and not starts_with_letter_name(name):
            return ["invalid name"]
        if self.invoice_count == 0:
            if name is not None:
                return [f"{name}: no such client"]
            return []
        if name is None:
            arr = sorted(self.invoices, key=lambda inv: (inv.name, inv.inv_id))
            return [f"{inv.inv_id} {money(inv.total_value)} {inv.name}" for inv in arr]
        arr = [inv for inv in self.invoices if inv.name == name]
        if not arr:
            return [f"{name}: no such client"]
        arr.sort(key=lambda inv: inv.inv_id)
        return [f"{inv.inv_id} {money(inv.total_value)} {inv.name}" for inv in arr]


def rand_name(rng: random.Random) -> str:
    pool = ["Rui", "Ana", "Bruno", "maria", "joao", "Cliente", "Xico", "manuel"]
    return rng.choice(pool)


def rand_desc_valid(rng: random.Random) -> str:
    head = rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    tail_len = rng.randint(2, 12)
    tail = "".join(rng.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(tail_len))
    return head + tail


def rand_desc_invalid(rng: random.Random) -> str:
    head = rng.choice("abcdefghijklmnopqrstuvwxyz0123456789")
    tail = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rng.randint(1, 8)))
    return head + tail


def make_valid_ean(rng: random.Random, length: int) -> str:
    body = "".join(rng.choice("0123456789") for _ in range(length - 1))
    s = 0
    for i, ch in enumerate(body):
        d = ord(ch) - 48
        s += d if i % 2 == 0 else d * 3
    check = (10 - (s % 10)) % 10
    return body + str(check)


def make_invalid_ean(rng: random.Random) -> str:
    if rng.random() < 0.5:
        e = make_valid_ean(rng, rng.choice([8, 13]))
        bad = (int(e[-1]) + rng.randint(1, 9)) % 10
        return e[:-1] + str(bad)
    bad_len = rng.choice([1, 2, 7, 9, 12])
    return "".join(rng.choice("0123456789") for _ in range(bad_len))


def dump_failure_artifacts(
    base: Path,
    input_text: str,
    expected_text: str,
    out_text: str,
    stderr_text: str,
    reason: str,
) -> None:
    base.parent.mkdir(parents=True, exist_ok=True)
    base.with_suffix(".in").write_text(input_text, encoding="utf-8")
    base.with_suffix(".expected").write_text(expected_text, encoding="utf-8")
    base.with_suffix(".out").write_text(out_text, encoding="utf-8")
    base.with_suffix(".stderr").write_text(stderr_text, encoding="utf-8")
    base.with_suffix(".reason").write_text(reason + "\n", encoding="utf-8")


def run_one(seed: int, run_id: int, steps: int, exe: Path, fail_dir: Path, timeout_s: int) -> bool:
    rng = random.Random(seed + run_id * 9973)
    model = Model()
    cmd_lines: list[str] = []
    expected: list[str] = []

    def pick_existing_ean() -> str | None:
        if not model.products:
            return None
        return rng.choice(list(model.products.keys()))

    for _ in range(steps):
        op = rng.choices(
            population=["p", "a", "f", "d", "r", "l", "c"],
            weights=[28, 24, 12, 12, 10, 8, 6],
            k=1,
        )[0]

        if op == "p":
            valid = rng.random() < 0.7
            if valid:
                use_existing = model.products and rng.random() < 0.4
                ean = pick_existing_ean() if use_existing else make_valid_ean(rng, rng.choice([8, 13]))
                iva = rng.choice(["A", "B", "C", "D"])
                price_cents = rng.randint(1, 20000)
                qty = rng.randint(0, 30)
                desc = rand_desc_valid(rng)
            else:
                kind = rng.choice(["ean", "iva", "price", "qty", "desc"])
                ean = make_valid_ean(rng, rng.choice([8, 13]))
                iva = rng.choice(["A", "B", "C", "D"])
                price_cents = rng.randint(1, 20000)
                qty = rng.randint(0, 30)
                desc = rand_desc_valid(rng)
                if kind == "ean":
                    ean = make_invalid_ean(rng)
                elif kind == "iva":
                    iva = rng.choice(["E", "Z", "x"])
                elif kind == "price":
                    price_cents = rng.choice([0, -100])
                elif kind == "qty":
                    qty = -rng.randint(1, 20)
                else:
                    desc = rand_desc_invalid(rng)
            price_s = f"{price_cents / 100:.2f}"
            cmd_lines.append(f"p {ean} {iva} {price_s} {qty} {desc}")
            expected.extend(model.cmd_p(ean, iva, price_cents, qty, desc))

        elif op == "a":
            sub = rng.choices(["list", "one", "two"], weights=[18, 22, 60], k=1)[0]
            if sub == "list":
                cmd_lines.append("a")
                expected.extend(model.cmd_a_list())
            elif sub == "one":
                if rng.random() < 0.1:
                    token = str(rng.randint(-10, 10))
                    cmd_lines.append(f"a {token}")
                    expected.extend(model.cmd_a(token, 1))
                else:
                    ean = pick_existing_ean() if model.products and rng.random() < 0.75 else make_valid_ean(rng, rng.choice([8, 13]))
                    if rng.random() < 0.15:
                        ean = make_invalid_ean(rng)
                    cmd_lines.append(f"a {ean}")
                    expected.extend(model.cmd_a(ean, 1))
            else:
                ean = pick_existing_ean() if model.products and rng.random() < 0.75 else make_valid_ean(rng, rng.choice([8, 13]))
                if rng.random() < 0.15:
                    ean = make_invalid_ean(rng)
                qty = rng.choice(
                    [
                        -15,
                        -10,
                        -5,
                        -2,
                        -1,
                        0,
                        1,
                        2,
                        3,
                        5,
                        10,
                        20,
                    ]
                )
                cmd_lines.append(f"a {qty} {ean}")
                expected.extend(model.cmd_a(ean, qty))

        elif op == "f":
            sub = rng.choices(["default", "name", "nif_name", "error"], weights=[20, 35, 35, 10], k=1)[0]
            if sub == "default":
                cmd_lines.append("f")
                expected.extend(model.cmd_f("999999999", "Cliente final"))
            elif sub == "error":
                cmd_lines.append("f error")
                expected.extend(model.cmd_f("999999999", "error"))
            elif sub == "name":
                name = rand_name(rng) if rng.random() < 0.8 else rng.choice(["8ball", "_rui"])
                cmd_lines.append(f"f {name}")
                expected.extend(model.cmd_f("999999999", name))
            else:
                nif = "".join(rng.choice("0123456789") for _ in range(9)) if rng.random() < 0.75 else rng.choice(
                    ["12345678", "1234567890", "12345678A", "abc"]
                )
                name = rand_name(rng) if rng.random() < 0.8 else rng.choice(["8ball", "_rui"])
                cmd_lines.append(f"f {nif} {name}")
                # For two unquoted args, parser always treats the first token as NIF.
                expected.extend(model.cmd_f(nif, name))

        elif op == "d":
            if rng.random() < 0.45:
                inv_id = rng.randint(-2, model.invoice_count + 3)
                cmd_lines.append(f"d {inv_id}")
                expected.extend(model.cmd_d_invoice(inv_id))
            else:
                ean = pick_existing_ean() if model.products and rng.random() < 0.75 else make_valid_ean(rng, rng.choice([8, 13]))
                if rng.random() < 0.15:
                    ean = make_invalid_ean(rng)
                qty = rng.choice([-5, -1, 0, 1, 2, 3, 5, 10, 30])
                cmd_lines.append(f"d {ean} {qty}")
                expected.extend(model.cmd_d_product(ean, qty))

        elif op == "r":
            if rng.random() < 0.5:
                cmd_lines.append("r")
                expected.extend(model.cmd_r(None))
            else:
                ean = pick_existing_ean() if model.products and rng.random() < 0.75 else make_valid_ean(rng, rng.choice([8, 13]))
                if rng.random() < 0.2:
                    ean = make_invalid_ean(rng)
                cmd_lines.append(f"r {ean}")
                expected.extend(model.cmd_r(ean))

        elif op == "l":
            if rng.random() < 0.4:
                cmd_lines.append("l")
                expected.extend(model.cmd_l(None))
            else:
                pats = []
                np = rng.randint(1, 3)
                for _ in range(np):
                    k = rng.choice(["*", "exact", "prefix", "nomatch", "q8", "q13"])
                    if k == "*":
                        pats.append("*")
                    elif k == "exact" and model.products:
                        pats.append(rng.choice(list(model.products.keys())))
                    elif k == "prefix" and model.products:
                        e = rng.choice(list(model.products.keys()))
                        pats.append(e[: rng.randint(1, len(e) - 1)] + "*")
                    elif k == "q8":
                        pats.append("?" * 8)
                    elif k == "q13":
                        pats.append("?" * 13)
                    else:
                        pats.append("999*")
                cmd_lines.append("l " + " ".join(pats))
                expected.extend(model.cmd_l(pats))

        else:  # c
            if rng.random() < 0.4:
                cmd_lines.append("c")
                expected.extend(model.cmd_c(None))
            else:
                choose_existing = model.invoices and rng.random() < 0.6
                if choose_existing:
                    name = rng.choice(model.invoices).name
                else:
                    name = rng.choice(["Rui", "Ana", "Bruno", "error", "8ball"])
                if any(ch in name for ch in (" ", "\t")):
                    cmd_lines.append(f'c "{name}"')
                else:
                    cmd_lines.append(f"c {name}")
                expected.extend(model.cmd_c(name))

    cmd_lines.append("q")
    input_text = "\n".join(cmd_lines) + "\n"
    expected_text = ("\n".join(expected) + "\n") if expected else ""

    base = fail_dir / f"seed_{seed}_run_{run_id}"
    try:
        proc = subprocess.run(
            [str(exe)],
            input=input_text.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        dump_failure_artifacts(
            base=base,
            input_text=input_text,
            expected_text=expected_text,
            out_text=(exc.stdout or b"").decode("utf-8", errors="replace"),
            stderr_text=(exc.stderr or b"").decode("utf-8", errors="replace"),
            reason=f"timeout after {timeout_s}s",
        )
        return False

    actual_text = proc.stdout.decode("utf-8", errors="replace")
    stderr_text = proc.stderr.decode("utf-8", errors="replace")
    if proc.returncode != 0:
        dump_failure_artifacts(
            base=base,
            input_text=input_text,
            expected_text=expected_text,
            out_text=actual_text,
            stderr_text=stderr_text,
            reason=f"exit_code={proc.returncode}",
        )
        return False

    if actual_text == expected_text:
        return True

    dump_failure_artifacts(
        base=base,
        input_text=input_text,
        expected_text=expected_text,
        out_text=actual_text,
        stderr_text=stderr_text,
        reason="output mismatch",
    )
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Random stress checker for proj using a shadow model.")
    parser.add_argument("--exe", default="../proj", help="Path to executable under test.")
    parser.add_argument("--runs", type=int, default=200, help="Number of random runs.")
    parser.add_argument("--steps", type=int, default=250, help="Commands per run (excluding q).")
    parser.add_argument("--seed", type=int, default=260315, help="Base RNG seed.")
    parser.add_argument("--timeout", type=int, default=8, help="Timeout in seconds per run.")
    parser.add_argument(
        "--fail-dir",
        default="stress-failures",
        help="Directory where failing cases are written.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=25,
        help="Print progress every N runs (0 disables progress).",
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
    for run_id in range(args.runs):
        ok = run_one(args.seed, run_id, args.steps, exe, fail_dir, args.timeout)
        if not ok:
            print(
                f"Mismatch found at run {run_id} (seed={args.seed}). "
                f"See {fail_dir}/seed_{args.seed}_run_{run_id}.*"
            )
            return 1
        if not args.quiet and args.progress_every > 0 and (run_id + 1) % args.progress_every == 0:
            print(f"passed {run_id + 1}/{args.runs} runs")

    print(f"All random stress runs passed: runs={args.runs}, steps={args.steps}, seed={args.seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
