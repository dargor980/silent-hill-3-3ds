"""AC01-AC10: bounded coordination through channel, custody and identity ports."""

import hashlib
import re
import struct
import time
from dataclasses import dataclass, replace

from tools.inspectors.effective_mapping import MappingContext, integer, validate_context
from tools.inspectors.observation_capture import ProfileError, require
from tools.inspectors.observer_capture import ObserverRequest, decode_reply
from tools.inspectors.observer_state import read_acquisition_state


@dataclass(frozen=True, repr=False)
class AcquisitionPlan:
    request: ObserverRequest
    context: MappingContext
    pid: int
    crc: int
    serial: str
    slot: int

    def validate(self):
        require(type(self.request) is ObserverRequest, "ACQUIRE_PLAN")
        self.request.validate()
        validate_context(self.context)
        require(
            self.context.session_id == self.request.session_id
            and self.context.sequence == self.request.sequence,
            "ACQUIRE_PLAN",
        )
        integer(self.pid, 1, 2**31 - 1, "ACQUIRE_PID")
        integer(self.crc, 1, 2**32 - 1, "ACQUIRE_CRC")
        integer(self.slot, 1, 99, "ACQUIRE_SLOT")
        require(
            isinstance(self.serial, str) and re.fullmatch(r"[A-Z]{4}-[0-9]{5}", self.serial),
            "ACQUIRE_SERIAL",
        )

    @property
    def state_name(self):
        return f"{self.serial} ({self.crc:08X}).{self.slot:02d}.p2s"


def _pine(channel, body, size):
    packet = channel.exchange(struct.pack("<I", len(body) + 4) + body)
    require(
        type(packet) is bytes
        and len(packet) == size + 5
        and packet[:5] == struct.pack("<IB", size + 5, 0),
        "ACQUIRE_PINE",
    )
    return packet[5:]


def _identity(channel, plan):
    require(_pine(channel, b"\x0f", 4) == struct.pack("<I", 1), "ACQUIRE_PAUSE")
    expected = struct.pack("<I", 9) + f"{plan.crc:08x}".encode() + b"\0"
    require(_pine(channel, b"\x0d", 13) == expected, "ACQUIRE_CRC")


def _memory(channel, request):
    data = bytearray()
    # Read8 batches avoid alignment assumptions; request <= 2,564 bytes.
    for start in range(0, request.size, 512):
        count = min(512, request.size - start)
        commands = b"".join(
            struct.pack("<BI", 0, request.virtual_start + start + i) for i in range(count)
        )
        data.extend(_pine(channel, commands, count))
    return bytes(data)


def _collect_acquisition(
    plan, channel, store, guard, *, timeout=30, clock=time.monotonic, wait=time.sleep
):
    """Ports are supplied by the trusted launcher; no success escapes a failed close.

    guard.check(plan) must validate the executable, profile, process and endpoint.
    store is a context manager exposing absent/read/put and checking its root at exit.
    This proves coherence of supplied observations, not authenticated execution.
    """
    plan.validate()
    require(type(timeout) in (float, int) and 0 < timeout <= 30, "ACQUIRE_TIMEOUT_VALUE")
    deadline = clock() + timeout

    def budget():
        remaining = deadline - clock()
        require(remaining > 0, "ACQUIRE_DEADLINE")
        return remaining

    context = replace(plan.context, state_sha256="0" * 64)
    request = plan.request
    first_identity = guard.check(plan)
    budget()
    with store:
        store.absent(plan.state_name)
        with channel:
            require(channel.peer_pid() == plan.pid, "ACQUIRE_PEER")
            _identity(channel, plan)
            a = channel.exchange(request.encode())
            observation = decode_reply(a, request, context)
            require(
                observation.pid == plan.pid and observation.game_crc == plan.crc, "ACQUIRE_IDENTITY"
            )
            budget()
            store.absent(plan.state_name)
            _pine(channel, struct.pack("<BB", 9, plan.slot), 0)
            for _ in range(256):
                budget()
                b = channel.exchange(request.encode())
                try:
                    second = decode_reply(b, request, context)
                except ProfileError as error:
                    if error.code != "OBSERVER_SAVE_PENDING":
                        raise
                    wait(min(0.05, budget()))
                    continue
                break
            else:
                require(False, "ACQUIRE_POLL_BUDGET")
            require(observation == second, "ACQUIRE_CHANGED")
            raw, digest = store.read(plan.state_name)
            require(hashlib.sha256(raw).hexdigest() == digest, "ACQUIRE_STATE_HASH")
            bound = replace(context, state_sha256=digest)
            observation = decode_reply(a, request, bound)
            state = read_acquisition_state(
                raw, plan.crc, observation.mapping.physical_offset, request.size
            )
            require(
                (state.cpu.pc, state.cycle, state.data)
                == (observation.pc, observation.cycle, observation.data),
                "ACQUIRE_STATE",
            )
            budget()
            require(_memory(channel, request) == observation.data, "ACQUIRE_MEMORY")
            _identity(channel, plan)
            c = channel.exchange(request.encode())
            require(
                decode_reply(b, request, bound) == observation == decode_reply(c, request, bound),
                "ACQUIRE_CHANGED",
            )
            current, current_digest = store.read(plan.state_name)
            require(current_digest == digest and current == raw, "ACQUIRE_STATE_CHANGED")
            budget()
            hashes = {}
            for label, packet in (("a", a), ("b", b), ("c", c)):
                name = f"{request.session_id}-{request.sequence:03d}-{label}.bin"
                store.put(name, packet)
                hashes[label] = hashlib.sha256(packet).hexdigest()
        # Socket is closed before filesystem final validation/release.
    require(guard.check(plan) == first_identity, "ACQUIRE_IDENTITY_CHANGED")
    budget()
    return {
        "schema_version": 1,
        "status": "consistent_supplied_acquisition",
        "session_id": request.session_id,
        "sequence": request.sequence,
        "environment_sha256": context.environment_sha256,
        "process_sha256": context.process_sha256,
        "state_sha256": digest,
        "packet_sha256": hashes,
        "content_size": request.size,
        "page_count": observation.mapping.page_count,
        "matches_expected_backing": observation.mapping.matches_expected_backing,
        "state_binding_verified": True,
        "live_acquisition_verified": False,
        "execution_authentication": "not_provided",
        "mp08_status": "pending",
    }


def collect_acquisition(*args, **kwargs):
    try:
        return _collect_acquisition(*args, **kwargs)
    except OSError:
        raise ProfileError("ACQUIRE_IO", "Acquisition I/O failed") from None


def acquire_and_publish(plan, channel, store, guard, output, *, publish, **kwargs):
    """Never call the publisher while an acquisition reader or socket is open."""
    result = collect_acquisition(plan, channel, store, guard, **kwargs)
    publish(output, result)
    return result


def acquire_local(plan, guard, repository, output):
    """Compose real ports from one launch receipt; no VM launch or UI mutation."""
    from tools.inspectors.observer_files import PrivateAcquisitionStore, publish_acquisition
    from tools.inspectors.observer_transport import Session

    return acquire_and_publish(
        plan,
        Session(str(guard.socket_path), timeout=30),
        PrivateAcquisitionStore(guard.state_root, repository),
        guard,
        output,
        publish=publish_acquisition,
    )
