#!/usr/bin/env python3
import argparse
import subprocess
import tempfile
from pathlib import Path


def ean8_from_base(n: int) -> str:
    base = f"{n:07d}"
    s = 0
    for i, ch in enumerate(base):
        d = ord(ch) - 48
        s += d if i % 2 == 0 else d * 3
    cd = (10 - (s % 10)) % 10
    return base + str(cd)


def build_input(path: Path, products: int, invoices: int, base_start: int) -> tuple[str, str]:
    main_ean = ean8_from_base(base_start)
    extra_ean = ean8_from_base(base_start + products)
    stock = invoices + 10

    with path.open("w", encoding="utf-8") as f:
        for i in range(products):
            ean = ean8_from_base(base_start + i)
            qty = stock if i == 0 else 1
            f.write(f"p {ean} A 1.00 {qty} P{i}\n")
        # One above MAX_PRODUCTS (10000) must fail as "invalid product"
        f.write(f"p {extra_ean} A 1.00 1 Extra\n")

        for i in range(1, invoices + 1):
            nif = f"{(100000000 + i) % 1000000000:09d}"
            name = f"C{i}"
            f.write(f"a {main_ean}\n")
            f.write(f"f {nif} {name}\n")

        f.write("r\n")
        f.write(f"c C{invoices}\n")
        f.write("q\n")
    return main_ean, extra_ean


def check_output(path: Path, products: int, invoices: int) -> list[str]:
    errors = []
    idx_invalid_product = products
    idx_first_invoice_line = products + 1 + 1
    idx_last_invoice_line = products + 1 + (invoices - 1) * 2 + 1
    idx_summary = products + 1 + invoices * 2
    idx_iva_a = idx_summary + 1
    idx_iva_b = idx_summary + 2
    idx_iva_c = idx_summary + 3
    idx_iva_d = idx_summary + 4
    idx_client = idx_summary + 5

    wanted = {
        idx_invalid_product,
        idx_first_invoice_line,
        idx_last_invoice_line,
        idx_summary,
        idx_iva_a,
        idx_iva_b,
        idx_iva_c,
        idx_iva_d,
        idx_client,
    }
    got = {}
    total_lines = 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            total_lines = i + 1
            if i in wanted:
                got[i] = line.rstrip("\n")

    expected_extra = "invalid product" if products >= 10000 else "1"
    if got.get(idx_invalid_product) != expected_extra:
        errors.append(
            f"Expected {expected_extra!r} at line {idx_invalid_product + 1}, got: {got.get(idx_invalid_product)!r}"
        )

    if got.get(idx_first_invoice_line) != "1 1.00 1":
        errors.append(
            f"Expected first invoice line '1 1.00 1' at line {idx_first_invoice_line + 1}, got: {got.get(idx_first_invoice_line)!r}"
        )

    expected_last = f"1 1.00 {invoices}"
    if got.get(idx_last_invoice_line) != expected_last:
        errors.append(
            f"Expected last invoice line {expected_last!r} at line {idx_last_invoice_line + 1}, got: {got.get(idx_last_invoice_line)!r}"
        )

    expected_summary = f"{invoices} {invoices} {invoices:.2f}"
    if got.get(idx_summary) != expected_summary:
        errors.append(
            f"Expected summary {expected_summary!r} at line {idx_summary + 1}, got: {got.get(idx_summary)!r}"
        )

    if got.get(idx_iva_a) != "A 0%":
        errors.append(f"Expected IVA line 'A 0%' at line {idx_iva_a + 1}, got: {got.get(idx_iva_a)!r}")
    if got.get(idx_iva_b) != "B 6%":
        errors.append(f"Expected IVA line 'B 6%' at line {idx_iva_b + 1}, got: {got.get(idx_iva_b)!r}")
    if got.get(idx_iva_c) != "C 13%":
        errors.append(f"Expected IVA line 'C 13%' at line {idx_iva_c + 1}, got: {got.get(idx_iva_c)!r}")
    if got.get(idx_iva_d) != "D 23%":
        errors.append(f"Expected IVA line 'D 23%' at line {idx_iva_d + 1}, got: {got.get(idx_iva_d)!r}")

    expected_client = f"{invoices} 1.00 C{invoices}"
    if got.get(idx_client) != expected_client:
        errors.append(
            f"Expected c-filter line {expected_client!r} at line {idx_client + 1}, got: {got.get(idx_client)!r}"
        )

    min_expected_lines = idx_client + 1
    if total_lines < min_expected_lines:
        errors.append(f"Output too short: got {total_lines} lines, expected at least {min_expected_lines}.")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Scale test: 10000 products + high invoice counts.")
    parser.add_argument("--exe", default="../proj", help="Path to executable")
    parser.add_argument("--products", type=int, default=10000, help="Number of products to insert")
    parser.add_argument("--invoices", type=int, default=100001, help="Number of invoices to emit")
    parser.add_argument("--base-start", type=int, default=1000000, help="Base for generating EAN-8 values")
    parser.add_argument("--timeout", type=int, default=600, help="Process timeout in seconds")
    args = parser.parse_args()

    exe = Path(args.exe)
    if not exe.exists():
        print(f"Executable not found: {exe}")
        return 2
    if args.products < 1 or args.invoices < 1:
        print("products and invoices must be >= 1")
        return 2

    with tempfile.TemporaryDirectory(prefix="scale_") as td:
        td_path = Path(td)
        in_path = td_path / "scale.in"
        out_path = td_path / "scale.out"

        main_ean, extra_ean = build_input(in_path, args.products, args.invoices, args.base_start)
        print(
            f"Running scale test: products={args.products}, invoices={args.invoices}, "
            f"main_ean={main_ean}, extra_ean={extra_ean}"
        )

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

        errors = check_output(out_path, args.products, args.invoices)
        if errors:
            print("Scale test FAILED:")
            for err in errors:
                print(f"- {err}")
            print(f"Input file for debugging: {in_path}")
            print(f"Output file for debugging: {out_path}")
            return 1

    print("Scale test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
