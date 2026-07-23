# Derivative work of Tierra Simulator — see legacy/tierra/license.h
"""Int2Lbl / Lbl2Int (Tierra portable.c, non-BIGNAMES)."""

from __future__ import annotations


def int_to_lbl(n: int) -> str:
    if n < 0:
        return "---"
    n = int(n)
    c0 = n // 676
    rem = n % 676
    c1 = rem // 26
    c2 = rem % 26
    return chr(ord("a") + c0) + chr(ord("a") + c1) + chr(ord("a") + c2)


def lbl_to_int(label: str) -> int:
    if not label or label == "---" or len(label) < 3:
        return -1
    a, b, c = label[0], label[1], label[2]
    if not (a.isalpha() and b.isalpha() and c.isalpha()):
        return -1
    return (ord(a.lower()) - ord("a")) * 676 + (ord(b.lower()) - ord("a")) * 26 + (
        ord(c.lower()) - ord("a")
    )


def parse_genotype_name(name: str) -> tuple[int, str] | None:
    if len(name) < 7:
        return None
    size_s, label = name[:4], name[4:]
    if not size_s.isdigit() or len(label) < 3:
        return None
    return int(size_s), label[:3]
