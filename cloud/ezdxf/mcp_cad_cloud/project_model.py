"""Versioned, CAD-independent architectural project model (MVP 1.0 / F1).

All dimensions are metres. No implicit normative compliance is asserted.
This module intentionally does not change the legacy drawing generators.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any
import json

SCHEMA_VERSION = 1
KINDS = {"rooms", "walls", "openings", "fixtures"}


class ProjectModelError(ValueError):
    """Invalid or incompatible architectural model."""


def _positive(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProjectModelError(f"{label} must be a positive finite number")
    number = float(value)
    if not isfinite(number) or number <= 0:
        raise ProjectModelError(f"{label} must be a positive finite number")
    return number


def _coordinate(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProjectModelError(f"{label} must be finite")
    number = float(value)
    if not isfinite(number):
        raise ProjectModelError(f"{label} must be finite")
    return number


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectModelError(f"{label} must be a nonempty string")
    return value


@dataclass
class Element:
    id: str
    geometry: dict[str, Any]
    relationships: dict[str, list[str]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Element":
        if not isinstance(raw, dict):
            raise ProjectModelError("element must be an object")
        return cls(
            id=raw.get("id"),
            geometry=raw.get("geometry"),
            relationships=raw.get("relationships", {}),
            metadata=raw.get("metadata", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "geometry": self.geometry,
            "relationships": self.relationships, "metadata": self.metadata,
        }


@dataclass
class ProjectModel:
    project_id: str
    lot: dict[str, Any]
    rooms: list[Element] = field(default_factory=list)
    walls: list[Element] = field(default_factory=list)
    openings: list[Element] = field(default_factory=list)
    fixtures: list[Element] = field(default_factory=list)
    revision: int = 0
    schema_version: int = SCHEMA_VERSION
    units: str = "m"

    def validate(self) -> None:
        _identifier(self.project_id, "project_id")
        if type(self.schema_version) is not int or self.schema_version != SCHEMA_VERSION:
            raise ProjectModelError("unsupported schema_version")
        if self.units != "m":
            raise ProjectModelError("units must be metres (m)")
        if type(self.revision) is not int or self.revision < 0:
            raise ProjectModelError("revision must be a nonnegative integer")
        if not isinstance(self.lot, dict):
            raise ProjectModelError("lot must be an object")
        _positive(self.lot.get("width"), "lot.width")
        _positive(self.lot.get("depth"), "lot.depth")
        index: dict[str, str] = {}
        for kind in sorted(KINDS):
            elements = getattr(self, kind)
            if not isinstance(elements, list):
                raise ProjectModelError(f"{kind} must be an array")
            for element in elements:
                if not isinstance(element, Element):
                    raise ProjectModelError(f"{kind} entries must be elements")
                key = _identifier(element.id, "element.id")
                if key in index:
                    raise ProjectModelError(f"duplicate element id: {key}")
                index[key] = kind
                if not isinstance(element.geometry, dict):
                    raise ProjectModelError(f"{key}: geometry must be an object")
                geometry = element.geometry
                if "x" not in geometry or "y" not in geometry:
                    raise ProjectModelError(f"{key}: x and y required")
                _coordinate(geometry["x"], f"{key}.x")
                _coordinate(geometry["y"], f"{key}.y")
                for dimension in ("width", "depth", "length", "thickness", "height"):
                    if dimension in geometry:
                        _positive(geometry[dimension], f"{key}.{dimension}")
                if not isinstance(element.relationships, dict):
                    raise ProjectModelError(f"{key}: relationships must be an object")
                if not isinstance(element.metadata, dict):
                    raise ProjectModelError(f"{key}: metadata must be an object")
        for kind in KINDS:
            for element in getattr(self, kind):
                for relation, targets in element.relationships.items():
                    if not isinstance(relation, str) or not isinstance(targets, list):
                        raise ProjectModelError(f"{element.id}: invalid relationship")
                    for target in targets:
                        if not isinstance(target, str) or target not in index:
                            raise ProjectModelError(f"{element.id}: unknown reference {target!r}")
        try:
            json.dumps(self.to_dict(), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ProjectModelError("model must be finite and JSON serializable") from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version, "project_id": self.project_id,
            "units": self.units, "revision": self.revision, "lot": self.lot,
            **{kind: [e.to_dict() for e in getattr(self, kind)] for kind in
               ("rooms", "walls", "openings", "fixtures")},
        }

    def to_json(self) -> str:
        self.validate()
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False, allow_nan=False)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ProjectModel":
        if not isinstance(raw, dict):
            raise ProjectModelError("project must be an object")
        model = cls(
            project_id=raw.get("project_id"), lot=raw.get("lot"),
            rooms=[Element.from_dict(e) for e in raw.get("rooms", [])],
            walls=[Element.from_dict(e) for e in raw.get("walls", [])],
            openings=[Element.from_dict(e) for e in raw.get("openings", [])],
            fixtures=[Element.from_dict(e) for e in raw.get("fixtures", [])],
            revision=raw.get("revision", 0),
            schema_version=raw.get("schema_version"),
            units=raw.get("units"),
        )
        model.validate()
        return model

    @classmethod
    def from_json(cls, payload: str) -> "ProjectModel":
        try:
            raw = json.loads(payload, parse_constant=lambda value: (_ for _ in ()).throw(
                ProjectModelError(f"nonfinite JSON constant: {value}")
            ))
        except (TypeError, ValueError) as exc:
            raise ProjectModelError("invalid project JSON") from exc
        return cls.from_dict(raw)
