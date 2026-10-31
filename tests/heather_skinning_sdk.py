"""HS-T2: run inside the pinned SDK, producing only compile/static evidence."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.heather_skinning_oracle import shader_program  # noqa: E402

OUT = (
    Path(sys.argv[1]).resolve()
    if len(sys.argv) > 1
    else ROOT / "build/heather-skinning-contract/sdk"
)
OUT.mkdir(parents=True, exist_ok=True)
PIC = "/opt/devkitpro/tools/bin/picasso"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


shader = ROOT / "tests/fixtures/synthetic/heather-skinning-v1.v.pica"


def compile_shader(name, text, success):
    src = OUT / (name + ".pica")
    dst = OUT / (name + ".shbin")
    src.write_text(text)
    p = subprocess.run([PIC, "-o", str(dst), str(src)], capture_output=True, text=True)
    assert (p.returncode == 0) == success, (name, p.returncode, p.stderr, p.stdout)
    return dict(
        name=name,
        returncode=p.returncode,
        stdout=p.stdout,
        stderr=p.stderr,
        source_sha256=sha(src),
        binary_sha256=sha(dst) if success else None,
    )


# These are compiler acceptance checks, not GPU executions.
body = ".out p position\n.proc main\nmov p, v0\nend\n.end\n"
checks = [compile_shader("contract", shader.read_text(), True)]
for n in (95, 96, 97):
    checks.append(compile_shader("uniforms-" + str(n), f".fvec x[{n}]\n" + body, n <= 96))
checks.append(
    compile_shader("31-matrices", shader.read_text().replace("palette[90]", "palette[93]"), False)
)
checks.append(compile_shader("96-plus-constant", ".fvec x[96]\n.constf c(0,1,0,0)\n" + body, False))
for r, success in [
    ("v11", True),
    ("v12", True),
    ("v14", True),
    ("v15", False),
    ("v16", False),
    ("r15", True),
    ("r16", False),
    ("c95", True),
    ("c96", False),
]:
    checks.append(
        compile_shader("register-" + r, body.replace("mov p, v0", "mov p, " + r), success)
    )
checks.append(compile_shader("two-inputs", body.replace("mov p, v0", "mul p, v0, v1"), False))
src = ROOT / "tests/fixtures/synthetic/heather-skinning-sdk-v1.cpp"
cmd = [
    "/opt/devkitpro/devkitARM/bin/arm-none-eabi-g++",
    "-std=c++17",
    "-Wall",
    "-Wextra",
    "-Werror",
    "-D__3DS__",
    "-march=armv6k",
    "-mfloat-abi=hard",
    "-mtp=soft",
    "-I/opt/devkitpro/libctru/include",
    "-c",
    str(src),
    "-o",
    str(OUT / "layout.o"),
]
p = subprocess.run(cmd, capture_output=True, text=True)
assert p.returncode == 0, p.stderr
packages = subprocess.check_output(
    ["dkp-pacman", "-Q", "citro3d", "libctru", "picasso", "devkitARM"], text=True
)
frozen = json.loads(
    (ROOT / "tests/fixtures/synthetic/heather-skinning-native-v1.json").read_bytes()
)
assert (OUT / "contract.shbin").read_bytes() == bytes.fromhex(frozen["shader_hex"])
assert len(shader_program((OUT / "contract.shbin").read_bytes())) == 28
report = dict(
    stage="HS-T2",
    sdk_image=(ROOT / "toolchains/devkitpro-image.txt").read_text().strip(),
    packages=packages,
    checks=checks,
    arm_layout=dict(command=cmd, source_sha256=sha(src), object_sha256=sha(OUT / "layout.o")),
    sdk_binaries={
        str(p): sha(p)
        for p in map(
            Path,
            [
                PIC,
                "/opt/devkitpro/libctru/lib/libcitro3d.a",
                "/opt/devkitpro/libctru/lib/libctru.a",
            ],
        )
    },
    gpu_executed=False,
)
(OUT / "probe.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(dict(checks=len(checks), arm_layout="PASS", report=str(OUT / "probe.json"))))
