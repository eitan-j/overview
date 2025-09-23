from __future__ import annotations

import glob
import json
from collections import defaultdict

from fontTools.ttLib import TTFont
from youseedee import parse_file_ranges, ucd_data

# TODO: force download
# it will only check if data is more than 3 mos old
# it could happen if a new emporor is unexpectedly coronated
# or something
# i dont think the VM caches this anyways

font_files = {}
noto_codepoints: dict[int, list[str]] = defaultdict(list)

sources = [
    "notofonts.github.io/fonts/Noto*/unhinted/ttf/Noto*-Regular.ttf",
    "noto-cjk/Sans/OTF/*/NotoSansCJK??-Regular.otf",
    "noto-emoji/fonts/NotoColorEmoji.ttf",
]
for source in sources:
    for fontfile in glob.glob(source):
        font = TTFont(fontfile)
        font_name = font["name"].getDebugName(1).replace("Noto ", "")
        font_files[font_name] = fontfile
        for k in font.getBestCmap().keys():
            noto_codepoints[k].append(font_name)


block_ranges = sorted(parse_file_ranges("Blocks.txt"))
blocks = []
for ix, (start, end, name) in enumerate(block_ranges):
    if (
        "Private Use Area" in name
        or "Surrogates" in name
        or "Variation Selectors" in name
        or name == "Tags"
    ):
        continue
    print("Processing %s" % name)
    coverage = "all"
    has_some = False
    cps: dict[int, dict[str, str | bool | list[str]]] = {}
    summary = ""
    for cp in range(start, end + 1):
        ucd = ucd_data(cp)
        if "Age" not in ucd:  # Unassigned
            summary += "X"
            continue
        cps[cp] = {"age": ucd["Age"]}
        if "Name" in ucd:
            cps[cp]["name"] = ucd["Name"]
        if ucd.get("General_Category", "") == "Cc" or cp == 32:
            cps[cp]["special"] = True
            summary += "S"
            continue
        if cp not in noto_codepoints:
            summary += "0"
            coverage = "partial"
        if cp in noto_codepoints and noto_codepoints[cp]:
            has_some = True
            cps[cp]["fonts"] = list(sorted(noto_codepoints[cp]))
            if len(noto_codepoints[cp]) > 1:
                summary += "M"
            else:
                summary += "1"
    if not has_some:
        coverage = "none"
    this_block = {
        "name": name,
        "start": start,
        "end": end,
        "coverage": coverage,
        "cps": cps,
    }
    ages = [cp["age"] for cp in cps.values()]
    if all(a == ages[0] for a in ages):
        this_block["age"] = ages[0]
        for cpd in cps.values():
            del cpd["age"]
    if coverage == "all":
        fontset = [cp["fonts"] for cp in cps.values() if "fonts" in cp]
        if all(f == fontset[0] for f in fontset[1:]):
            this_block["fonts"] = fontset[0]
            for cp in this_block["cps"].values():
                del cp["fonts"]
    json.dump(this_block, open("blocks/block-%03i.json" % ix, "w"))
    summary_block = {
        "ix": ix,
        "name": name,
        "start": start,
        "end": end,
        "coverage": coverage,
        "summary": summary,
    }
    blocks.append(summary_block)

json.dump(blocks, open("blocks.json", "w"))
json.dump(dict(sorted(font_files.items())), open("fontfiles.json", "w"))
