"""HS-T1: structural SRI2 workload and ordered opaque palette partitions.

Capacities are analytical inputs, not PICA uniform limits. This does not deform
vertices, time the runtime or reorder transparent triangles. No original assets
are embedded; callers own authentication and publication of private evidence.
"""

from collections import Counter

from tools.qa.locomotion_rig_oracle import reconstruct_sri2

# Native RigPalette uses the fixed primary capacity, not the active bone count.
RIG_BONE_CAPACITY = 73
DEFAULT_CAPACITIES = (8, 12, 16, 24, 32, 48, 64, 96)


def partition_palettes(triangles, capacity):
    """Maximal contiguous batches; (first triangle, count, sorted palette).

    Matrix identities must already be validated. A triangle is indivisible.
    Empty input produces no batches. Failure returns no partial partition.
    """
    if type(capacity) is not int or not 1 <= capacity <= 201:
        raise ValueError("HS_CAPACITY")
    batches, palette, first = [], set(), 0
    for ordinal, triangle in enumerate(triangles):
        required = set(triangle)
        if not required or len(required) > capacity:
            raise ValueError("HS_TRIANGLE_CAPACITY")
        if len(palette | required) > capacity:
            batches.append((first, ordinal - first, sorted(palette)))
            first, palette = ordinal, set()
        palette.update(required)
    if palette:
        batches.append((first, ordinal + 1 - first, sorted(palette)))
    return batches


def _slots(vertex):
    return (vertex[11], *(RIG_BONE_CAPACITY + h for h in vertex[13 : 12 + vertex[12]]))


def _histogram(values):
    return {str(k): n for k, n in sorted(Counter(values).items())}


def _summary(model, indices):
    vertices = model["vertices"]
    unique = sorted(set(indices))
    slots = sorted({s for i in unique for s in _slots(vertices[i])})
    return dict(
        indices=len(indices),
        triangles=len(indices) // 3,
        unique_vertices=len(unique),
        influences=_histogram(vertices[i][12] for i in unique),
        weight_sums_q12=_histogram(sum(vertices[i][8:11]) for i in unique),
        zero_weight_active_influences=sum(
            w == 0 for i in unique for w in vertices[i][8 : 8 + vertices[i][12]]
        ),
        matrix_slots=slots,
        primary_matrices=sum(s < RIG_BONE_CAPACITY for s in slots),
        helper_matrices=sum(s >= RIG_BONE_CAPACITY for s in slots),
        unique_vertex_influence_evaluations=sum(vertices[i][12] for i in unique),
        expanded_vertex_influence_evaluations=sum(vertices[i][12] for i in indices),
    )


def analyze_sri2(raw, capacities=DEFAULT_CAPACITIES):
    """Validate SRI2 first; report geometry shared by all its clips.

    Texture bytes/manifest authentication are outside this pure function.
    Transparent palette counts describe storage only, never a valid draw plan.
    """
    capacities = tuple(capacities)
    if not capacities or len(set(capacities)) != len(capacities):
        raise ValueError("HS_CAPACITIES")
    for capacity in capacities:
        partition_palettes((), capacity)
    model = reconstruct_sri2(raw)
    vertices, indices = model["vertices"], model["indices"]
    opaque, blended, materials, plans = [], [], [], {str(c): [] for c in capacities}
    rejected = {str(c): [] for c in capacities}
    for ordinal, material in enumerate(model["materials"]):
        first, count, _, _, _, blend, _ = material
        selected = indices[first : first + count]
        (blended if blend else opaque).extend(selected)
        triangles = [
            {s for i in selected[j : j + 3] for s in _slots(vertices[i])}
            for j in range(0, count, 3)
        ]
        materials.append(
            dict(
                material=ordinal,
                blend=bool(blend),
                first_index=first,
                max_triangle_matrices=max(map(len, triangles)),
                **_summary(model, selected),
            )
        )
        if blend:
            continue
        for capacity in capacities:
            key = str(capacity)
            try:
                batches = partition_palettes(triangles, capacity)
            except ValueError:
                rejected[key].append(ordinal)
                continue
            for start, length, palette in batches:
                refs = set(selected[start * 3 : (start + length) * 3])
                plans[key].append(
                    dict(
                        material=ordinal,
                        first_index=first + start * 3,
                        index_count=length * 3,
                        matrix_slots=palette,
                        unique_vertices=len(refs),
                    )
                )
    curves = []
    for capacity in capacities:
        key = str(capacity)
        # Do not publish a partial plan if any opaque material is infeasible.
        batches = [] if rejected[key] else plans[key]
        curves.append(
            dict(
                capacity=capacity,
                feasible=not rejected[key],
                rejected_materials=rejected[key],
                batches=batches,
                batch_count=len(batches),
                matrix_uploads=sum(len(b["matrix_slots"]) for b in batches),
                vertices_if_duplicated_per_batch=sum(b["unique_vertices"] for b in batches),
            )
        )
    return dict(
        schema="heather-skinning-workload-v1",
        scope="structural_only_no_hardware_measurement",
        profile=model["profile"],
        clips=[c[0] for c in model["clips"]],
        samples=len(model["samples"]),
        bones=len(model["bones"]),
        helpers=len(model["helpers"]),
        stored_vertices=len(vertices),
        unreferenced_vertices=len(vertices) - len(set(indices)),
        current_cpu_influence_evaluations=sum(v[12] for v in vertices),
        current_palette_matrices=len(model["bones"]) + len(model["helpers"]),
        all_referenced=_summary(model, indices),
        opaque=_summary(model, opaque),
        blended=_summary(model, blended),
        shared_opaque_blended_vertices=len(set(opaque) & set(blended)),
        helper_targets=[h[0] for h in model["helpers"]],
        materials=materials,
        opaque_capacity_curve=curves,
    )
