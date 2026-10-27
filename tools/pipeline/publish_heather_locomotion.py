"""Exclusive external SRI2 publication from authenticated original source bytes."""

import os

from tools.pipeline.private_texture_output import _write_bundle
from tools.pipeline.produce_heather_locomotion import produce_heather_locomotion
from tools.qa.locomotion_rig_oracle import reconstruct_sri2_bundle

OUTPUT_NAMES = {"heather.sri"} | {f"texture-{i:02}.rgba" for i in range(13)}


def publish_heather_locomotion(root, repository, run_id, model, animation, descriptors):
    """Never overwrite a destination; publish the manifest only after readback.

    Raw source pins and structural reconstruction are checked here. Fidelity
    against captured poses is a separate audit; publication alone does not
    certify that audit or a console build.
    """
    files, report = produce_heather_locomotion(model, animation, descriptors)
    expected = reconstruct_sri2_bundle(files)

    def verify(directory_fd, _manifest):
        actual = {}
        for name, original in files.items():
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
            with os.fdopen(fd, "rb") as stream:
                data = stream.read(len(original) + 1)
            if data != original:
                raise ValueError("HL_PUBLICATION_READBACK")
            actual[name] = data
        if reconstruct_sri2_bundle(actual) != expected:
            raise ValueError("HL_PUBLICATION_RECONSTRUCTION")

    report["publication"] = "source_pinned_structural_readback"
    report["pose_reference_audit"] = "separate_required"
    return _write_bundle(
        root, repository, run_id, files, report, OUTPUT_NAMES, before_publish=verify
    )
