"""DIC4 manuscript self-check; does not mutate models or historic evidence."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "dic4"
EVAL = ROOT / "docs" / "midterm" / "public_test_results.json"


def check_latex(source: str, bib: str, label: str) -> dict[str, object]:
    assert "\\begin{document}" in source and "\\end{document}" in source, label
    assert source.count("\\begin{") == source.count("\\end{"), label
    # Balance only genuine LaTeX grouping braces, ignoring \{ and \}.
    depth = 0
    for match in re.finditer(r"(?<!\\)[{}]", source):
        depth += 1 if match.group() == "{" else -1
        assert depth >= 0, f"{label}: closing brace without opener"
    assert depth == 0, f"{label}: unbalanced grouping"
    cites = {
        item.strip()
        for group in re.findall(r"\\cite(?:\[[^\]]*\])?\{([^{}]+)\}", source)
        for item in group.split(",")
    }
    keys = set(re.findall(r"@\w+\s*\{\s*([^,\s{}]+)\s*,", bib))
    missing = sorted(cites - keys)
    assert not missing, f"{label}: missing bibliography keys: {missing}"
    return {"cited_keys": sorted(cites), "bib_keys": sorted(keys)}


def main() -> None:
    results = {}
    for version in ("v1_before", "v2_after"):
        directory = PAPER / version
        results[version] = check_latex(
            (directory / "main.tex").read_text(encoding="utf-8"),
            (directory / "references.bib").read_text(encoding="utf-8"),
            version,
        )

    data = json.loads(EVAL.read_text(encoding="utf-8"))["horizons"]
    revised = (PAPER / "v2_after" / "main.tex").read_text(encoding="utf-8")
    for h, expected_n, expected_up in (("h=7", 2085, 16), ("h=14", 1859, 23)):
        item = data[h]
        selected = item["selected"]
        momentum = item["baselines"]["past_change_continues"]
        unchanged = item["baselines"]["flat_no_change"]
        assert selected["n"] == expected_n == item["n"]
        assert selected["direction"]["confusion_matrix"][2][2] == expected_up
        assert selected["direction"]["macro_f1"] < momentum["direction"]["macro_f1"]
        assert selected["return_mae"] > unchanged["return_mae"]
        for val in (
            selected["direction"]["macro_f1"],
            momentum["direction"]["macro_f1"],
            selected["return_mae"],
            unchanged["return_mae"],
        ):
            assert f"{val:.4f}" in revised, (h, val)
        assert str(expected_n) in revised.replace(",", ""), "n appears in LaTeX"
        results[h] = {
            "n": expected_n,
            "model_f1": selected["direction"]["macro_f1"],
            "momentum_f1": momentum["direction"]["macro_f1"],
            "model_mae": selected["return_mae"],
            "unchanged_mae": unchanged["return_mae"],
            "up_true_positive": expected_up,
            "up_support": int(selected["direction"]["per_class"]["up"]["support"]),
        }

    for marker in ("\\section{Introduction}", "\\section{Related Work", "\\section{Architecture", "\\section{Frozen", "\\section{Prospective", "\\section{Conclusion}"):
        assert marker in revised, f"missing section: {marker}"
    print(json.dumps({"status": "STATIC_CHECK_PASS", "scope": "text/bibliography/frozen-numbers only", "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
