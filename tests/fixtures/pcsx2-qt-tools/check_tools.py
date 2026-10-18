"""Verify actual Linguist tool output through independent XML/hash oracles."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

EXPECTED = {("Open door", "action"), ("Key", "item"), ("Key", "keyboard"), ("Moon: 🌙", ""), ("%n key(s)", "")}

def run(argv, valid=True):
    result = subprocess.run(list(map(str, argv)), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    print(result.stdout, end="")
    if valid:
        assert result.returncode == 0, result.returncode
    else:
        assert result.returncode != 0 and result.stdout.strip(), "Expected rejection with diagnostic"
    return result

def messages(path):
    root = ET.parse(path).getroot()
    assert root.tag == "TS" and root.attrib["language"] == "es_ES"
    contexts = root.findall("context")
    assert len(contexts) == 1 and contexts[0].findtext("name") == "Fixture"
    entries = contexts[0].findall("message")
    result = {(m.findtext("source"), m.findtext("comment", "")): m for m in entries}
    assert len(entries) == len(result) and set(result) == EXPECTED
    assert result[("%n key(s)", "")].attrib.get("numerus") == "yes"
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=["extract", "release", "invalid"])
    for name in ["lupdate", "lrelease", "source", "work"]:
        parser.add_argument("--"+name, required=True, type=Path)
    args = parser.parse_args()
    work = args.work / args.case
    work.mkdir(parents=True, exist_ok=True)
    if args.case == "extract":
        extracted = work / "extracted.ts"
        if extracted.exists(): extracted.unlink()
        run([args.lupdate, args.source / "messages.cpp", "-locations", "none", "-target-language", "es_ES", "-ts", extracted])
        messages(extracted)
        existing = work / "updated.ts"
        shutil.copyfile(args.source / "es.ts", existing)
        before = {k: ET.tostring(v.find("translation")) for k,v in messages(existing).items()}
        run([args.lupdate, args.source / "messages.cpp", "-locations", "none", "-ts", existing])
        after = {k: ET.tostring(v.find("translation")) for k,v in messages(existing).items()}
        # XML formatting can change; compare text/type/forms semantically.
        def value(raw):
            node=ET.fromstring(raw)
            return node.attrib, (node.text or "").strip(), [child.text for child in node]
        assert {k:value(v) for k,v in before.items()} == {k:value(v) for k,v in after.items()}
    elif args.case == "release":
        outputs = [work / "first.qm", work / "second.qm"]
        for output in outputs: run([args.lrelease, args.source / "es.ts", "-qm", output])
        assert outputs[0].stat().st_size > 0 and outputs[0].read_bytes() == outputs[1].read_bytes()
        print("Identical QM SHA256:", hashlib.sha256(outputs[0].read_bytes()).hexdigest())
    else:
        for name, source in [("malformed", args.source / "invalid.ts"), ("missing", work / "absent.ts")]:
            output = work / (name+".qm")
            if output.exists(): output.unlink()
            run([args.lrelease, source, "-qm", output], valid=False)
            assert not output.exists(), "Failed compilation created QM"
        run([args.lupdate, work / "absent.cpp", "-ts", work / "missing.ts"], valid=False)
    print("PASS", args.case)

if __name__ == "__main__":
    main()
