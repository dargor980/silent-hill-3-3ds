"""Parse bounded IT traces without turning incomplete work into successful samples."""

PHASES = frozenset(
    (
        "prepare manifest_parse construct sample initial manifest_before origin_first "
        "origin_second manifest_after digest tail close_work file_identity file_read "
        "sha_update origin_stable"
    ).split()
)
PARTITION = "initial manifest_before origin_first origin_second manifest_after digest tail".split()
FINE = {"file_identity", "file_read", "sha_update", "origin_stable"}


def parse(lines, mode, accepted):
    if (
        mode not in {"clean", "coarse", "fine"}
        or type(accepted) is not int
        or not 0 <= accepted <= 3
    ):
        raise ValueError("invalid session metadata")
    phases, events, ends = {}, [], {}
    for line in lines:
        if not line.startswith("IT_"):
            continue
        parts = line.split()
        pairs = [p.split("=", 1) for p in parts[1:]]
        if any(len(p) != 2 for p in pairs) or len(dict(pairs)) != len(pairs):
            raise ValueError("malformed timing row")
        row = dict(pairs)
        role = row.pop("role", None)
        if role not in {"IO", "DW"}:
            raise ValueError("invalid role")
        if parts[0] == "IT_PHASE":
            phase = row.pop("phase", None)
            required = {
                "query",
                "calls",
                "complete",
                "total_ns",
                "min_ns",
                "max_ns",
                "bytes",
                "first_ns",
                "last_ns",
            }
            if role != "DW" or phase not in PHASES or set(row) != required:
                raise ValueError("invalid phase")
        elif parts[0] == "IT_EVENT":
            event = row.pop("event", None)
            required = {"query", "at_ns", "deadline_ns"}
            if (
                role != "IO"
                or event
                not in {"open", "binding", "submit", "delivered", "cleanup_begin", "cleanup_end"}
                or set(row) != required
            ):
                raise ValueError("invalid event")
        elif parts[0] == "IT_END":
            if (
                set(row) != {"fine", "errors", "calibration_calls", "calibration_ns"}
                or role in ends
            ):
                raise ValueError("invalid end")
        else:
            raise ValueError("unknown timing marker")
        if any(
            not v.isascii() or not v.isdecimal() or len(v) > 20 or int(v) > 2**64 - 1
            for v in row.values()
        ):
            raise ValueError("invalid numeric value")
        row = {k: int(v) for k, v in row.items()}
        if role in ends:
            raise ValueError("row after terminal marker")
        if parts[0] == "IT_PHASE":
            q = row["query"]
            if (
                q > 3
                or not row["calls"]
                or row["complete"] > row["calls"]
                or row["min_ns"] > row["max_ns"]
                or row["last_ns"] < row["first_ns"]
                or not row["min_ns"] * row["calls"]
                <= row["total_ns"]
                <= row["max_ns"] * row["calls"]
                or row["total_ns"] > row["last_ns"] - row["first_ns"]
            ):
                raise ValueError("inconsistent phase counter")
            if (q, phase) in phases or (mode != "fine" and phase in FINE):
                raise ValueError("duplicate or unexpected phase")
            phases[q, phase] = row
        elif parts[0] == "IT_EVENT":
            if (
                row["query"] > 3
                or any(e["event"] == event and e["query"] == row["query"] for e in events)
                or len(events) == 16
            ):
                raise ValueError("duplicate or excessive event")
            if events and row["at_ns"] < events[-1]["at_ns"]:
                raise ValueError("backward event clock")
            events.append(dict(row, event=event))
        else:
            if row["errors"] or row["fine"] != (mode == "fine"):
                raise ValueError("probe error or wrong mode")
            ends[role] = row
    if mode == "clean":
        if phases or events or ends:
            raise ValueError("clean candidate contains instrumentation")
        return dict(instrumented=False, queries=[])
    if (
        set(ends) != {"IO", "DW"}
        or ends["IO"]["calibration_calls"] != 10000
        or not ends["IO"]["calibration_ns"]
        or ends["DW"]["calibration_calls"]
    ):
        raise ValueError("incomplete instrumentation")
    lookup = {(e["event"], e["query"]): e for e in events}
    try:
        opened, cb, ce = (lookup[n, 0] for n in ["open", "cleanup_begin", "cleanup_end"])
        if opened["deadline_ns"] - opened["at_ns"] != 5_000_000_000:
            raise ValueError("global budget changed")
        queries = []
        for q in range(1, 4):
            subset = {p: r for (i, p), r in phases.items() if i == q and p != "close_work"}
            submit, delivery = lookup.get(("submit", q)), lookup.get(("delivered", q))
            if not submit:
                if subset or delivery or q <= accepted:
                    raise ValueError("sample without submission")
                continue
            if (
                submit["deadline_ns"] > opened["deadline_ns"]
                or not 0 < submit["deadline_ns"] - submit["at_ns"] <= (5 if q == 1 else 2) * 10**9
            ):
                raise ValueError("query budget changed")
            sample = subset.get("sample")
            complete = bool(sample and sample["complete"] == sample["calls"] == 1)
            if q <= accepted and (not complete or not delivery):
                raise ValueError("accepted incomplete sample")
            if complete and (
                not all(
                    p in subset and subset[p]["complete"] == subset[p]["calls"] == 1
                    for p in PARTITION
                )
                or sum(subset[p]["total_ns"] for p in PARTITION) > sample["total_ns"]
            ):
                raise ValueError("overlapping or incomplete phase partition")
            if complete:
                previous_end = sample["first_ns"]
                for phase in PARTITION:
                    part = subset[phase]
                    if part["first_ns"] < previous_end or part["last_ns"] > sample["last_ns"]:
                        raise ValueError("phase outside ordered sample partition")
                    previous_end = part["last_ns"]
            queries.append(
                dict(
                    query=q,
                    completed=complete,
                    accepted=q <= accepted,
                    phases=subset,
                    submit=submit,
                    delivery=delivery,
                    delivery_margin_ns=None
                    if delivery is None
                    else submit["deadline_ns"] - delivery["at_ns"],
                    sample_margin_ns=None
                    if sample is None
                    else submit["deadline_ns"] - sample["last_ns"],
                )
            )
        return dict(
            instrumented=True,
            preparation={p: r for (q, p), r in phases.items() if q == 0},
            queries=queries,
            events=events,
            calibration=ends["IO"],
            cleanup_ns=ce["at_ns"] - cb["at_ns"],
            global_margin_at_cleanup_ns=opened["deadline_ns"] - cb["at_ns"],
        )
    except KeyError as exc:
        raise ValueError("missing timing event") from exc
