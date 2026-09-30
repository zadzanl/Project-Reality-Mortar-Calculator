"""Decode the locally observed Battlefield 2 compiled road mesh format.

This reader intentionally supports the road mesh layout observed in the
Project Reality v1.9 Asad Khal fixture.  It is not a general Battlefield 2
mesh or navigation-mesh reader.  A future format version needs a new fixture
and an explicit decoder branch rather than a speculative fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import struct
from typing import Iterable
import zipfile
import zlib

import numpy as np


HEADER_MAGIC = b"\x04\x00\x01\x00"
VERTEX_OFFSET = 52
VERTEX_STRIDE_BYTES = 32
VERTEX_FLOATS = 8
POSITION_FLOATS = 3
FOOTER_HEADER_BYTES = 4
FOOTER_RECORD_BYTES = 24


class RoadMeshError(ValueError):
    """Raised when a road reference or compiled mesh is not self-consistent."""


@dataclass(frozen=True)
class RoadMesh:
    """Decoded geometry and retained metadata for one compiled road mesh."""

    source_name: str
    origin: np.ndarray
    vertices: np.ndarray
    vertex_attributes: np.ndarray
    triangles: np.ndarray
    header_triplets: np.ndarray
    header_value_40: float
    header_value_44: int
    index_count: int
    footer_records: tuple[tuple[int, int, float, float, float, float], ...]
    file_size: int
    bytes_consumed: int


@dataclass(frozen=True)
class MeshReference:
    """A compiledroads.con reference and its normalized client archive key."""

    reference: str
    archive_name: str
    object_name: str


@dataclass(frozen=True)
class MeshAccounting:
    """Reference and byte accounting from a strict archive load."""

    reference_count: int
    unique_reference_count: int
    resolved_count: int
    decoded_count: int
    referenced_bytes: int
    decoded_bytes: int
    duplicate_references: tuple[str, ...]
    missing_references: tuple[str, ...]
    decode_errors: tuple[str, ...]
    unreferenced_meshes: tuple[str, ...]

    @property
    def unreferenced_mesh_count(self) -> int:
        """Return the number of road mesh files not named by the manifest."""
        return len(self.unreferenced_meshes)


_MESH_REFERENCE_RE = re.compile(
    r"^\s*object\.geometry\.loadMesh\s+(\S+)\s*$", re.IGNORECASE
)


def _checked_end(start: int, size: int, total: int, label: str) -> int:
    """Return a section end or raise an actionable truncation error."""
    if start < 0 or size < 0:
        raise RoadMeshError(f"{label} has a negative offset or size")
    end = start + size
    if end > total:
        raise RoadMeshError(
            f"{label} exceeds mesh size: end {end}, file size {total}"
        )
    return end


def _as_readonly_bytes(data: bytes | bytearray | memoryview) -> memoryview:
    """Return a byte view and reject values that cannot represent raw bytes."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("compiled mesh data must be bytes-like")
    view = memoryview(data)
    if view.ndim != 1 or view.itemsize != 1:
        view = memoryview(view.tobytes())
    return view.cast("B")


def decode_compiled_road_mesh(
    data: bytes | bytearray | memoryview, source_name: str = ""
) -> RoadMesh:
    """Decode one compiled road mesh from bytes.

    Positions are returned in local BF2 mesh coordinates as float32 ``N x 3``
    values.  The mesh origin is the float32 triplet at byte offset 4.  The
    observed remainder after the index buffer is retained as opaque footer
    records because its semantic names are not proven by the local fixtures.
    """
    raw = _as_readonly_bytes(data)
    file_size = len(raw)
    if file_size < VERTEX_OFFSET:
        raise RoadMeshError(
            f"{source_name or '<mesh>'}: file is too small for the 52-byte header"
        )
    if raw[:4].tobytes() != HEADER_MAGIC:
        actual = raw[:4].tobytes().hex()
        raise RoadMeshError(
            f"{source_name or '<mesh>'}: unsupported header bytes {actual}"
        )

    origin = np.asarray(struct.unpack_from("<3f", raw, 4), dtype=np.float32)
    header_triplets = np.asarray(
        (
            struct.unpack_from("<3f", raw, 16),
            struct.unpack_from("<3f", raw, 28),
        ),
        dtype=np.float32,
    )
    header_value_40 = struct.unpack_from("<f", raw, 40)[0]
    header_value_44 = struct.unpack_from("<I", raw, 44)[0]
    vertex_count = struct.unpack_from("<I", raw, 48)[0]
    if not np.isfinite(origin).all() or not np.isfinite(header_triplets).all():
        raise RoadMeshError(f"{source_name or '<mesh>'}: header floats are not finite")
    if not np.isfinite(header_value_40):
        raise RoadMeshError(
            f"{source_name or '<mesh>'}: header value at 40 is not finite"
        )
    if vertex_count == 0:
        raise RoadMeshError(f"{source_name or '<mesh>'}: vertex count is zero")

    vertex_bytes = vertex_count * VERTEX_STRIDE_BYTES
    vertex_end = _checked_end(
        VERTEX_OFFSET, vertex_bytes, file_size, "vertex buffer"
    )
    vertex_rows = np.frombuffer(
        raw, dtype="<f4", count=vertex_count * VERTEX_FLOATS, offset=VERTEX_OFFSET
    ).reshape((vertex_count, VERTEX_FLOATS))
    if not np.isfinite(vertex_rows).all():
        raise RoadMeshError(f"{source_name or '<mesh>'}: vertex data is not finite")
    vertices = vertex_rows[:, :POSITION_FLOATS].copy()
    vertex_attributes = vertex_rows[:, POSITION_FLOATS:].copy()

    if vertex_end + 4 > file_size:
        raise RoadMeshError(
            f"{source_name or '<mesh>'}: missing index count after vertex buffer"
        )
    index_count = struct.unpack_from("<I", raw, vertex_end)[0]
    if index_count == 0 or index_count % 3:
        raise RoadMeshError(
            f"{source_name or '<mesh>'}: index count {index_count} is not a "
            "non-zero triangle-list count"
        )
    index_offset = vertex_end + 4
    index_end = _checked_end(
        index_offset, index_count * 2, file_size, "index buffer"
    )
    indices = np.frombuffer(
        raw, dtype="<u2", count=index_count, offset=index_offset
    ).copy()
    if int(indices.max()) >= vertex_count:
        raise RoadMeshError(
            f"{source_name or '<mesh>'}: index {int(indices.max())} is outside "
            f"vertex range 0..{vertex_count - 1}"
        )
    triangles = indices.reshape((-1, 3))

    footer_size = file_size - index_end
    if footer_size < FOOTER_HEADER_BYTES:
        raise RoadMeshError(
            f"{source_name or '<mesh>'}: footer is only {footer_size} bytes"
        )
    footer_count = struct.unpack_from("<I", raw, index_end)[0]
    expected_footer_size = FOOTER_HEADER_BYTES + footer_count * FOOTER_RECORD_BYTES
    if expected_footer_size != footer_size:
        raise RoadMeshError(
            f"{source_name or '<mesh>'}: footer size {footer_size} does not "
            f"match count {footer_count} and 24-byte records "
            f"({expected_footer_size})"
        )
    footer_records = tuple(
        struct.unpack_from(
            "<II4f", raw, index_end + FOOTER_HEADER_BYTES + i * FOOTER_RECORD_BYTES
        )
        for i in range(footer_count)
    )
    if footer_records and not np.isfinite(
        np.asarray([record[2:] for record in footer_records], dtype=np.float32)
    ).all():
        raise RoadMeshError(f"{source_name or '<mesh>'}: footer data is not finite")

    return RoadMesh(
        source_name=source_name,
        origin=origin.copy(),
        vertices=vertices,
        vertex_attributes=vertex_attributes,
        triangles=triangles,
        header_triplets=header_triplets,
        header_value_40=header_value_40,
        header_value_44=header_value_44,
        index_count=index_count,
        footer_records=footer_records,
        file_size=file_size,
        bytes_consumed=file_size,
    )


def decode_road_mesh(
    data: bytes | bytearray | memoryview, source_name: str = ""
) -> RoadMesh:
    """Backward-compatible short alias for decode_compiled_road_mesh."""
    return decode_compiled_road_mesh(data, source_name)


def road_vertices_world(
    mesh: RoadMesh, position: Iterable[float] | None = None
) -> np.ndarray:
    """Return vertices translated from local coordinates into BF2 world space.

    If ``position`` is omitted, the mesh header origin is used.  The optional
    position is a three-value BF2 X/Y/Z origin and is useful when a caller has
    an authoritative object position from compiledroads.con.
    """
    if position is None:
        translation = mesh.origin
    else:
        translation = np.asarray(tuple(position), dtype=np.float32)
        if translation.shape != (3,) or not np.isfinite(translation).all():
            raise ValueError("position must contain three finite values")
    return np.asarray(mesh.vertices + translation, dtype=np.float32)


def normalize_mesh_reference(reference: str, map_name: str) -> str:
    """Map a compiledroads.con path to a normalized client archive key."""
    if not isinstance(reference, str) or not reference or "\x00" in reference:
        raise RoadMeshError("mesh reference must be a non-empty string")
    if not isinstance(map_name, str) or not map_name or "/" in map_name:
        raise RoadMeshError("map_name must be a simple non-empty name")
    normalized = reference.replace("\\", "/")
    parts = normalized.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise RoadMeshError(f"invalid mesh reference path: {reference}")
    if len(parts) != 4 or parts[0].lower() != "levels":
        raise RoadMeshError(f"unexpected mesh reference path: {reference}")
    if parts[1].lower() != map_name.lower() or parts[2].lower() != "roads":
        raise RoadMeshError(
            f"mesh reference is not a road for map {map_name}: {reference}"
        )
    basename = parts[3]
    if not basename.lower().endswith("_compiled.mesh"):
        raise RoadMeshError(f"not a compiled road mesh: {reference}")
    return f"roads/{basename}".lower()


def extract_mesh_references(
    compiledroads_text: str, map_name: str
) -> list[MeshReference]:
    """Extract road mesh references in compiledroads.con source order."""
    references: list[MeshReference] = []
    for line_number, line in enumerate(compiledroads_text.splitlines(), 1):
        if "object.geometry.loadmesh" not in line.lower():
            continue
        match = _MESH_REFERENCE_RE.match(line)
        if not match:
            raise RoadMeshError(
                f"malformed loadMesh record at compiledroads.con line {line_number}"
            )
        reference = match.group(1)
        archive_name = normalize_mesh_reference(reference, map_name)
        object_name = archive_name.rsplit("/", 1)[-1][:-len("_compiled.mesh")]
        references.append(
            MeshReference(
                reference=reference,
                archive_name=archive_name,
                object_name=object_name,
            )
        )
    return references


def _archive_members_by_key(archive: zipfile.ZipFile) -> dict[str, str]:
    """Index archive paths case-insensitively and reject ambiguous paths."""
    members: dict[str, str] = {}
    for member in archive.namelist():
        key = member.replace("\\", "/").lower()
        if key in members:
            raise RoadMeshError(
                f"archive contains duplicate case-insensitive path: {member}"
            )
        members[key] = member
    return members


def _find_compiledroads_member(members: dict[str, str]) -> str:
    """Find the unique compiledroads.con member in a server archive."""
    candidates = [
        member
        for key, member in members.items()
        if key.rsplit("/", 1)[-1] == "compiledroads.con"
    ]
    if len(candidates) != 1:
        raise RoadMeshError(
            f"expected one compiledroads.con member, found {len(candidates)}"
        )
    return candidates[0]


def _load_referenced_road_meshes(
    server_zip: str | Path,
    client_zip: str | Path,
    map_name: str,
    *,
    strict: bool = True,
) -> tuple[list[RoadMesh], MeshAccounting]:
    """Decode the unique road meshes named by a server archive manifest.

    The returned list preserves first-reference order.  Repeated manifest
    references are reported in accounting and are not decoded twice.
    Missing or malformed meshes raise in strict mode; in non-strict mode they
    are reported and omitted so callers can inspect partial data explicitly.
    """
    with zipfile.ZipFile(server_zip) as server_archive, zipfile.ZipFile(
        client_zip
    ) as client_archive:
        server_members = _archive_members_by_key(server_archive)
        client_members = _archive_members_by_key(client_archive)
        manifest_member = _find_compiledroads_member(server_members)
        text = server_archive.read(manifest_member).decode("latin1")
        references = extract_mesh_references(text, map_name)

        by_key: dict[str, MeshReference] = {}
        duplicate_references: list[str] = []
        for reference in references:
            if reference.archive_name in by_key:
                duplicate_references.append(reference.reference)
            else:
                by_key[reference.archive_name] = reference

        road_keys = {
            key
            for key in client_members
            if key.startswith("roads/") and key.endswith("_compiled.mesh")
        }
        unreferenced = tuple(sorted(road_keys - set(by_key)))
        missing = tuple(sorted(set(by_key) - set(client_members)))
        if strict and missing:
            raise RoadMeshError(
                "missing referenced road meshes: " + ", ".join(missing)
            )

        decoded: list[RoadMesh] = []
        referenced_bytes = 0
        decoded_bytes = 0
        errors: list[str] = []
        for archive_name, reference in by_key.items():
            member = client_members.get(archive_name)
            if member is None:
                continue
            try:
                data = client_archive.read(member)
            except (
                zipfile.BadZipFile,
                KeyError,
                OSError,
                RuntimeError,
                EOFError,
                zlib.error,
            ) as error:
                message = (
                    f"{reference.reference}: archive member {member}: {error}"
                )
                if strict:
                    raise RoadMeshError("road archive read error: " + message) from error
                errors.append(message)
                continue
            referenced_bytes += len(data)
            try:
                mesh = decode_compiled_road_mesh(data, member)
            except (RoadMeshError, struct.error, ValueError) as error:
                errors.append(f"{reference.reference}: {error}")
                continue
            decoded.append(mesh)
            decoded_bytes += len(data)

        if strict and errors:
            raise RoadMeshError("road mesh decode errors: " + " | ".join(errors))
        accounting = MeshAccounting(
            reference_count=len(references),
            unique_reference_count=len(by_key),
            resolved_count=len(by_key) - len(missing),
            decoded_count=len(decoded),
            referenced_bytes=referenced_bytes,
            decoded_bytes=decoded_bytes,
            duplicate_references=tuple(duplicate_references),
            missing_references=missing,
            decode_errors=tuple(errors),
            unreferenced_meshes=unreferenced,
        )
        if strict and accounting.resolved_count != accounting.decoded_count:
            raise RoadMeshError(
                f"decoded {accounting.decoded_count} of "
                f"{accounting.resolved_count} resolved road meshes"
            )
        return decoded, accounting


def load_referenced_road_meshes(
    server_zip: str | Path,
    client_zip: str | Path,
    map_name: str,
    *,
    strict: bool = True,
) -> tuple[list[RoadMesh], MeshAccounting]:
    """Load referenced road meshes and normalize expected archive failures."""
    try:
        return _load_referenced_road_meshes(
            server_zip, client_zip, map_name, strict=strict
        )
    except RoadMeshError:
        raise
    except (
        zipfile.BadZipFile,
        KeyError,
        OSError,
        RuntimeError,
        EOFError,
        zlib.error,
        UnicodeError,
    ) as error:
        raise RoadMeshError(f"road archive read error: {error}") from error


__all__ = [
    "MeshAccounting",
    "MeshReference",
    "RoadMesh",
    "RoadMeshError",
    "decode_compiled_road_mesh",
    "decode_road_mesh",
    "extract_mesh_references",
    "load_referenced_road_meshes",
    "normalize_mesh_reference",
    "road_vertices_world",
]