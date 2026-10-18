"""Read private TS files without Qt; emit private expectations, never vendor text to stdout."""
import argparse
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def read_catalog(path):
    root = ET.parse(path).getroot()
    assert root.tag == "TS", path.name
    dependencies = [node.attrib["catalog"] for node in root.findall("./dependencies/dependency")]
    messages = []
    for context in root.findall("context"):
        for message in context.findall("message"):
            translation = message.find("translation")
            if translation is None or translation.get("type") in {"unfinished", "vanished", "obsolete"}:
                continue
            plural = message.get("numerus") == "yes"
            if plural:
                assert {node.tag for node in translation} <= {"numerusform"}
                values = [node.text or "" for node in translation]
            else:
                assert len(translation) == 0, "Unsupported translation structure"
                values = [translation.text or ""]
            if not values or not all(values):
                continue
            # This oracle deliberately handles Spanish only; other plural rules differ.
            assert len(values) == (2 if plural else 1), path.name
            messages.append({"context": context.findtext("name"), "source": message.findtext("source"),
                             "comment": message.findtext("comment", ""), "plural": plural, "values": values})
    return {"catalog": path.stem, "language": root.attrib["language"],
            "dependencies": dependencies, "messages": messages}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--english", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    files = sorted(args.source.glob("*.ts")) + sorted(args.english.glob("*.ts"))
    assert len(files) > 291
    catalogs = []
    spanish = []
    for path in files:
        root = ET.parse(path).getroot()
        catalogs.append({"catalog": path.stem, "language": root.get("language", ""),
                         "dependencies": [x.attrib["catalog"] for x in root.findall("./dependencies/dependency")]})
        if root.get("language") in {"es", "es_ES"}:
            spanish.append(read_catalog(path))
    names = {item["catalog"] for item in catalogs}
    assert len(names) == len(catalogs)
    for item in catalogs:
        assert set(item["dependencies"]) <= names
    counts = Counter()
    for item in spanish:
        for message in item["messages"]:
            counts["messages"] += 1
            counts["plurals"] += message["plural"]
            counts["disambiguated"] += bool(message["comment"])
            counts["unicode_translations"] += any(ord(c) > 127 for value in message["values"] for c in value)
    assert len(spanish) == 13 and all(counts[key] > 0 for key in counts)
    assert next(x for x in spanish if x["catalog"] == "qt_es")["dependencies"] == ["qtbase_es", "qtmultimedia_es"]
    data = {"catalogs": catalogs, "spanish": spanish, "counts": dict(counts)}
    with args.output.open("x") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"catalogs": len(catalogs), "spanish_catalogs": len(spanish), **dict(counts)}))


if __name__ == "__main__":
    main()
