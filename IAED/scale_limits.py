#!/usr/bin/env python3
import argparse
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path


def ean8_from_base(n: int) -> str:
    base = f"{n:07d}"
    s = 0
    for i, ch in enumerate(base):
        d = ord(ch) - 48
        s += d if i % 2 == 0 else d * 3
    cd = (10 - (s % 10)) % 10
    return base + str(cd)


def build_input(
    path: Path,
    products: int,
    invoices: int,
    base_start: int,
    progress_every: int,
    quiet: bool,
) -> tuple[str, str]:
    main_ean = ean8_from_base(base_start)
    extra_ean = ean8_from_base(base_start + products)
    stock = invoices + 10

    with path.open("w", encoding="utf-8") as f:
        for i in range(products):
            ean = ean8_from_base(base_start + i)
            qty = stock if i == 0 else 1
            f.write(f"p {ean} A 1.00 {qty} P{i}\n")
            if not quiet and progress_every > 0 and (i + 1) % progress_every == 0:
                print(f"Input build progress (products): {i + 1}/{products}", flush=True)
        # One above MAX_PRODUCTS (10000) must fail as "invalid product"
        f.write(f"p {extra_ean} A 1.00 1 Extra\n")

        for i in range(1, invoices + 1):
            nif = f"{(100000000 + i) % 1000000000:09d}"
            name = f"C{i}"
            f.write(f"a {main_ean}\n")
            f.write(f"f {nif} {name}\n")
            if not quiet and progress_every > 0 and i % progress_every == 0:
                print(f"Input build progress (invoices): {i}/{invoices}", flush=True)

        f.write("r\n")
        f.write(f"c C{invoices}\n")
        f.write("q\n")
    return main_ean, extra_ean


def check_output(path: Path, products: int, invoices: int, progress_every: int, quiet: bool) -> list[str]:
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
            if not quiet and progress_every > 0 and (i + 1) % progress_every == 0:
                print(f"Output check progress: scanned {i + 1} lines", flush=True)

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


def dump_failure_artifacts(
    fail_dir: Path,
    prefix: str,
    in_path: Path,
    out_path: Path,
    stderr_data: bytes,
    reason: str,
    errors: list[str] | None = None,
) -> Path:
    fail_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    base = fail_dir / f"{prefix}_{stamp}"

    if in_path.exists():
        base.with_suffix(".in").write_bytes(in_path.read_bytes())
    if out_path.exists():
        base.with_suffix(".out").write_bytes(out_path.read_bytes())
    base.with_suffix(".stderr").write_bytes(stderr_data or b"")

    details = [reason]
    if errors:
        details.extend(errors)
    base.with_suffix(".reason").write_text("\n".join(details) + "\n", encoding="utf-8")
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description="Scale test: 10000 products + high invoice counts.")
    parser.add_argument("--exe", default="../proj", help="Path to executable")
    parser.add_argument("--products", type=int, default=10000, help="Number of products to insert")
    parser.add_argument("--invoices", type=int, default=100001, help="Number of invoices to emit")
    parser.add_argument("--base-start", type=int, default=1000000, help="Base for generating EAN-8 values")
    parser.add_argument("--timeout", type=int, default=600, help="Process timeout in seconds")
    parser.add_argument("--fail-dir", default="scale-failures", help="Where to persist failure artifacts.")
    parser.add_argument(
        "--progress-every",
        type=int,
        default=20000,
        help="Print progress every N products/invoices/lines (0 disables progress).",
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
    if args.products < 1 or args.invoices < 1:
        print("products and invoices must be >= 1")
        return 2

    fail_dir = Path(args.fail_dir)
    with tempfile.TemporaryDirectory(prefix="scale_") as td:
        td_path = Path(td)
        in_path = td_path / "scale.in"
        out_path = td_path / "scale.out"

        if not args.quiet:
            print(
                f"Running scale test: products={args.products}, invoices={args.invoices}, "
                f"main_ean_base={args.base_start}",
                flush=True,
            )
            print("Building input file...", flush=True)
        main_ean, extra_ean = build_input(
            in_path,
            args.products,
            args.invoices,
            args.base_start,
            args.progress_every,
            args.quiet,
        )
        if not args.quiet:
            print(
                f"Input build done: main_ean={main_ean}, extra_ean={extra_ean}. Running executable...",
                flush=True,
            )

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
            reason = f"timeout after {args.timeout}s"
            base = dump_failure_artifacts(
                fail_dir,
                "scale",
                in_path,
                out_path,
                exc.stderr or b"",
                reason,
            )
            print(f"Scale test FAILED: {reason}")
            print(f"Failure artifacts: {base}.*")
            return 1

        if proc.returncode != 0:
            reason = f"exit_code={proc.returncode}"
            base = dump_failure_artifacts(
                fail_dir,
                "scale",
                in_path,
                out_path,
                proc.stderr,
                reason,
            )
            print(f"Program exited with code {proc.returncode}")
            if proc.stderr:
                print(proc.stderr.decode("utf-8", errors="replace"))
            print(f"Failure artifacts: {base}.*")
            return 1

        if not args.quiet:
            print("Execution done. Checking output...", flush=True)
        errors = check_output(
            out_path,
            args.products,
            args.invoices,
            args.progress_every,
            args.quiet,
        )
        if errors:
            base = dump_failure_artifacts(
                fail_dir,
                "scale",
                in_path,
                out_path,
                proc.stderr,
                "output mismatch",
                errors,
            )
            print("Scale test FAILED:")
            for err in errors:
                print(f"- {err}")
            print(f"Failure artifacts: {base}.*")
            return 1

    print("Scale test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
