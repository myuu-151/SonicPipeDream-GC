"""Rewrite proj/Scripts/StageData<N>.lua so that no part of loading it needs one big block.

    python native/split_stage_data.py

A stage's data was one table constructor of ~5,000 lines in one ~200 KB file. To load it the engine
read the file whole (one block the file's size), and Lua compiled it into ONE function whose
instruction and constant arrays grow by doubling as it goes -- toward the end, one 256 KB block.
After a marathon and a stage or two, a GameCube's heap (5 MB free, in 2,400 pieces) had no hole that
big: the stage's data did not load, and the stage came up as stage 1. (MarathonKit had the same
trouble; patch_from_pc.py's split_kit splits it into files.)

So the table's small fields stay in StageData<N>.lua, and its long lists -- pieces, sections (and
each section's objects), path -- are filled a hundred entries at a time, each hundred a function of
its own, in files of about PART bytes (StageData<N>_1.lua, _2, ...) that StageData<N>.lua runs in
turn. Every block the loading needs is a few tens of KB. The table that results is the same, entry
for entry. Files already split are left alone; run it again after export_gc.py writes a stage.
"""
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "proj", "Scripts")
MARK = "-- (split by native/split_stage_data.py)"
BATCH = 100
PART = 24 * 1024
LISTS = ("pieces", "sections", "path")


def entries(lines, i, indent):
    """The entries of a list opened just before lines[i], each as its lines, and the index past
    its closing line. An entry is one line ("{...},") or a block ("{" ... "},")."""
    out = []
    close = " " * (indent - 2) + "},"
    while lines[i] != close:
        line = lines[i]
        assert line.startswith(" " * indent) and not line.startswith(" " * (indent + 1)), line
        if line.strip() == "{":
            j = i + 1
            while lines[j] != " " * indent + "},":
                j += 1
            out.append(lines[i:j + 1])
            i = j + 1
        else:
            out.append([line])
            i += 1
    return out, i + 1


def as_expr(entry):
    """An entry's lines as one expression (its trailing comma dropped)."""
    text = " ".join(l.strip() for l in entry)
    assert text.endswith(","), text[-40:]
    return text[:-1]


def batches(target, exprs):
    """Statements filling `target` with `exprs`, a function for each BATCH of them: each a chunk
    (a list of lines) of its own."""
    out = []
    for k in range(0, len(exprs), BATCH):
        chunk = ["fill = function() local t = %s" % target]
        chunk += ["t[#t + 1] = " + e for e in exprs[k:k + BATCH]]
        chunk.append("end fill()")
        out.append(chunk)
    return out


def split(path):
    text = open(path, encoding="utf-8").read()
    if MARK in text:
        return False
    lines = text.split("\n")
    name = re.match(r"^(StageData\d+) = \{$", next(l for l in lines if l.startswith("StageData"))).group(1)
    start = lines.index(name + " = {")
    head, top, chunks = lines[:start], [name + " = {"], []
    i = start + 1
    while lines[i] != "}":
        m = re.match(r"^  (\w+) = \{$", lines[i])
        if m and m.group(1) in LISTS:
            key = m.group(1)
            items, i = entries(lines, i + 1, 4)
            top.append("  %s = {}," % key)
            if key != "sections":
                chunks += batches("%s.%s" % (name, key), [as_expr(e) for e in items])
                continue
            # a section: its own fields, then its objects in batches of their own
            for s, entry in enumerate(items, 1):
                inner = entry[1:-1]
                fields, objects, k = [], [], 0
                while k < len(inner):
                    if inner[k] == "      objects = {":
                        objects, k = entries(inner, k + 1, 8)
                        fields.append("objects = {},")
                    else:
                        fields.append(inner[k].strip())
                        k += 1
                chunks.append(["%s.sections[%d] = { %s }" % (name, s, " ".join(fields))])
                chunks += batches("%s.sections[%d].objects" % (name, s), [as_expr(e) for e in objects])
            continue
        top.append(lines[i])
        i += 1

    # the chunks into files of about PART bytes each, in order
    base = os.path.splitext(path)[0]
    for old in glob.glob(base + "_*.lua"):
        os.remove(old)
    parts, part, size = [], [], 0
    for chunk in chunks:
        chunk_size = sum(len(l) + 1 for l in chunk)
        if part and size + chunk_size > PART:
            parts.append(part)
            part, size = [], 0
        part += chunk
        size += chunk_size
    if part:
        parts.append(part)
    for n, part in enumerate(parts, 1):
        with open("%s_%d.lua" % (base, n), "w", encoding="utf-8", newline="\n") as f:
            f.write("-- %s's data, part %d of %d: see native/split_stage_data.py.\n" % (name, n, len(parts)))
            f.write("local fill\n")
            f.write("\n".join(part) + "\n")
    run = 'for i = 1, %d do Script.Run("%s_" .. i) end     -- its lists, in pieces' % (len(parts), name)
    out = head + [MARK] + top + ["}", run] + lines[i + 1:]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    return True


def main():
    for path in sorted(glob.glob(os.path.join(SCRIPTS, "StageData[0-9].lua"))):
        print(os.path.basename(path), "split" if split(path) else "already split")


if __name__ == "__main__":
    main()
