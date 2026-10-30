"""Deterministic private SD archives with fixed viewer paths."""

import hashlib
import io
import zipfile


def inspection_archive(files: dict[str, bytes], stem: str) -> bytes:
    if stem not in {
        "sh3_texture_probe",
        "sh3_geometry_probe",
        "sh3_material_probe",
        "sh3_animation_probe",
        "sh3_character_probe",
        "sh3_character_material_probe",
        "sh3_character_lighting_probe",
        "sh3_character_world_probe",
        "sh3_heather_probe",
        "sh3_heather_room",
    }:
        raise ValueError("Unexpected inspection viewer")
    payload = "geometry.sgm" if stem == "sh3_geometry_probe" else "texture.stx"
    if stem in {
        "sh3_animation_probe",
        "sh3_character_probe",
        "sh3_character_material_probe",
        "sh3_character_lighting_probe",
        "sh3_character_world_probe",
    }:
        payload = "animation.san"
    expected = {payload, f"{stem}.3dsx", f"{stem}.smdh", "LEEME.txt"}
    if stem == "sh3_material_probe":
        expected.add("geometry.sgm")
    if stem in {
        "sh3_character_probe",
        "sh3_character_material_probe",
        "sh3_character_lighting_probe",
        "sh3_character_world_probe",
    }:
        expected.add("character.scm")
    if stem in {
        "sh3_character_material_probe",
        "sh3_character_lighting_probe",
        "sh3_character_world_probe",
    }:
        expected.add("character.sct")
    if stem == "sh3_character_lighting_probe":
        expected.add("character.scl")
    if stem == "sh3_character_world_probe":
        expected.add("character.scw")
    if stem == "sh3_heather_probe":
        expected = {
            "heather.sri",
            f"{stem}.3dsx",
            f"{stem}.smdh",
            "LEEME.txt",
        } | {f"texture-{i:02}.rgba" for i in range(13)}
    if stem == "sh3_heather_room":
        expected = {
            "scene.srr",
            "map.srm",
            "glass.rgba",
            "heather.sri",
            f"{stem}.3dsx",
            f"{stem}.smdh",
            "LEEME.txt",
        } | {f"texture-{i:02}.rgba" for i in range(13)}
    if stem == "sh3_heather_room" and "room-texture-00.rgba" in files:
        expected |= {f"room-texture-{i:02}.rgba" for i in range(9)}
    if set(files) != expected:
        raise ValueError("Unexpected inspection archive files")
    contents = {f"3ds/{stem}/{name}": data for name, data in files.items()}
    contents["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(contents.items())
    ).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(contents.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100600 << 16
            archive.writestr(info, data)
    return output.getvalue()
