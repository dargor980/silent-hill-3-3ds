"""HM-T4b.3: pure, pinned hp34 contact preparation; no private paths or I/O."""

from fractions import Fraction

from tools.pipeline.decoders.ps2_cld_polygons import decode_polygons
from tools.pipeline.intermediate_assets import fields, sha, verify_file
from tools.pipeline.intermediate_json import decode_json, encode_json

PROFILE_PIN = dict(
    size=3585, sha256="5838c4b445a0da3f4a2636ac9c9e61edfe754dc89b33d25db33284581212e531"
)
PROFILE = "heather-hp34-contacts-v1"
LIMITS = {
    "source.cld": 65536,
    "room-profile.json": 16384,
    "polygons.json": 131072,
    "contacts.json": 32768,
}
GROUP_COUNTS = [1, 4, 26, 3, 0]
ORIGIN = [100000, 0, 140000]


def require(condition, code):
    if not condition:
        raise ValueError(code)


def equal(actual, expected, code="HRC_PREP_PROFILE"):
    require(encode_json(actual) == encode_json(expected), code)


def read_profile(raw):
    verify_file(raw, PROFILE_PIN)
    profile = decode_json(raw)
    equal(profile["profile"], "heather-hp34-inspection-v1")
    equal(profile["schema_version"], 1)
    equal(profile["coordinates"]["origin"], ORIGIN)
    equal(profile["budgets"]["contact_working_bytes"], 4096)
    equal(
        profile["contacts"],
        {
            "profile": "static-xz-aabb-stop-v1",
            "cell": 0,
            "expected_group_counts": GROUP_COUNTS,
            "floor": {"group": 0, "index": 0},
            "ceiling_without_vertical_motion": {"group": 2, "index": 4},
            "other_referenced_records": "blocking_xz_aabb_regardless_of_filter_word",
            "expected_blockers": 32,
            "footprint_half_extent": 175,
            "guard": 1,
            "contact_boundary": "closed",
            "response": "reject_whole_translation_keep_from",
            "sweep": "continuous_segment_against_expanded_boxes",
            "vertical_motion": False,
            "sliding": False,
            "dynamic_actors": False,
        },
    )
    fields(profile["resources"], ("map", "collision", "external_texture"))
    return profile


def _box(record):
    # Preserve the first source word on numerical ties, including signed zero.
    points, words = record["vectors_xyzw"], record["vector_words"]
    result = []
    for axis in (0, 2):
        for pick in (min, max):
            index = pick(range(4), key=lambda i: points[i][axis])
            result.append(f"f32:{words[index][axis]:08x}")
    return result


def convert_cld(raw):
    """Geometry-only converter for this structural profile; not an identity bypass.

    Publication must use make_package, which authenticates source and room pins.
    The retained CP view preserves all W/opaque words and all 80 cell lists.
    """
    view = decode_polygons(raw)
    require(
        view["origin_xz"] == [ORIGIN[0], ORIGIN[2]] and view["selection_word"] == 0,
        "HRC_PREP_ORIGIN_SELECTION",
    )
    require([len(g["records"]) for g in view["groups"]] == GROUP_COUNTS, "HRC_PREP_COUNTS")
    roles, blockers = [], []
    for group in view["groups"]:
        count = len(group["records"])
        require(group["cells"][0]["indices"] == list(range(count)), "HRC_PREP_REFERENCES")
        require(all(not cell["indices"] for cell in group["cells"][1:]), "HRC_PREP_REFERENCES")
        for record in group["records"]:
            require(record["variant"] == 1 and record["point_count"] == 4, "HRC_PREP_VARIANT")
            require(
                all(abs(p[k]) <= 1000000 for p in record["vectors_xyzw"] for k in range(3)),
                "HRC_PREP_BOUNDS",
            )
            key = group["index"], record["index"]
            role = "floor" if key == (0, 0) else "ceiling_excluded" if key == (2, 4) else "blocker"
            roles.append(dict(group=key[0], index=key[1], offset=record["offset"], role=role))
            if role == "blocker":
                blockers.append(_box(record))
    floor = view["groups"][0]["records"][0]
    ceiling = view["groups"][2]["records"][4]
    require(all(p[1] == 0 for p in floor["vectors_xyzw"]), "HRC_PREP_FLOOR")
    require(all(p[1] == -1600 for p in ceiling["vectors_xyzw"]), "HRC_PREP_CEILING")
    points = {(p[0], p[2]) for p in floor["vectors_xyzw"]}
    xs, zs = {p[0] for p in points}, {p[1] for p in points}
    require(
        len(xs) == len(zs) == 2 and points == {(x, z) for x in xs for z in zs},
        "HRC_PREP_FLOOR_RECTANGLE",
    )
    require(
        Fraction(max(xs)) - Fraction(min(xs)) > 352 and Fraction(max(zs)) - Fraction(min(zs)) > 352,
        "HRC_PREP_EMPTY_FLOOR",
    )
    scene = dict(
        profile="static-xz-aabb-stop-v1",
        origin=ORIGIN.copy(),
        floor_y=0,
        half_extent=175,
        guard=1,
        floor=_box(floor),
        blockers=blockers,
    )
    return view, dict(schema_version=1, profile=PROFILE, scene=scene, record_roles=roles)


def make_package(raw, profile_raw):
    profile = read_profile(profile_raw)
    source = profile["resources"]["collision"]
    verify_file(raw, source)
    view, contacts = convert_cld(raw)
    contacts["source"] = source.copy()
    contacts["anchors"] = dict(
        room_profile_sha256=sha(profile_raw),
        catalog_sha256=profile["catalog_sha256"],
        extraction_receipt_sha256=profile["extraction_receipt_sha256"],
    )
    return {
        "source.cld": raw,
        "room-profile.json": profile_raw,
        "polygons.json": encode_json(view),
        "contacts.json": encode_json(contacts),
    }


def verify_package(files):
    fields(files, LIMITS)
    require(
        all(type(raw) is bytes and 0 < len(raw) <= LIMITS[name] for name, raw in files.items()),
        "HRC_PREP_PACKAGE_LIMIT",
    )
    expected = make_package(files["source.cld"], files["room-profile.json"])
    require(files == expected, "HRC_PREP_RECONSTRUCTION")
    profile = read_profile(files["room-profile.json"])
    return dict(
        schema_version=1,
        scope="private_hp34_contacts",
        profile=PROFILE,
        converter="hp34-contacts-prepare-v1",
        source=profile["resources"]["collision"],
        room_profile_sha256=sha(files["room-profile.json"]),
        catalog_sha256=profile["catalog_sha256"],
        extraction_receipt_sha256=profile["extraction_receipt_sha256"],
        counts=dict(records=34, floor=1, ceiling_excluded=1, blockers=32),
        source_preserved=True,
        scene_binding="native_composition_not_ps2_registration",
        new_vm_execution=False,
        runtime_integration=False,
    )
