"""Plain report for pipes, CI and screen readers. Same words as the TUI, no layout."""
from __future__ import annotations

from .model import Session
from .theme import Theme
from .widgets import glyph_raw, pad


def render_plain(th: Theme, s: Session) -> str:
    word = lambda st: th.paint(st.role, f"{glyph_raw(th, st)} {st.word}")  # noqa: E731
    dim = lambda t: th.paint("t3", t)  # noqa: E731
    bw = max([5] + [len(b.plain or b.value) for b in s.bays])
    nw = max([4] + [len(f.name) for f in s.findings])
    vw = max([4] + [len(f.value) for f in s.findings])
    c = {"fail": 0, "warn": 0, "open": 0, "pass": 0}
    for f in s.findings:
        c[f.status.bucket] += 1
    lines = [f"xflash · offline · read only · {s.title}",
             dim(f"{pad('BAY', 4)} {pad('VALUE', bw)} STATUS"),
             dim(th.g["h"] * (4 + bw + 9))]
    lines += [f"{pad(b.name, 4)} {pad(b.plain or b.value, bw)} {word(b.status)}" for b in s.bays]
    lines.append(dim("RULES"))
    for f in s.findings:
        pre = word(f.status)
        lines.append(f"{pre}{' ' * max(1, 9 - len(f.status.word) - 2)}{pad(f.id, 7)} {pad(f.name.lower(), nw)} "
                     f"{pad(f.value, vw)} {dim(f.note)}".rstrip())
    tail = f"{c['fail']} fail · {c['warn']} warn · {c['open']} open · {c['pass']} pass"
    lines.append(tail + (f"    report {s.report_path}" if s.report_path else ""))
    return th.safe("\n".join(lines))
