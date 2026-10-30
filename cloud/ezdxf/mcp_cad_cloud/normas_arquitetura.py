"""Load and validate a small, explicitly non-exhaustive standards registry."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlparse

from mcp_cad_cloud.arquitetura_requisitos import RequirementRecord


_REGISTRY_PATH = Path(__file__).with_name("normas_arquitetura.json")
_ALLOWED_STATUSES = {"Em Vigor", "Não confirmado", "Cancelada"}


def validate_registry(payload: dict, *, as_of: date | None = None) -> None:
    today = as_of or date.today()
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Versão do registro normativo não suportada.")
    if payload.get("scope") != "candidate_standards_not_exhaustive":
        raise ValueError("Escopo precisa declarar que a lista não é exaustiva.")
    entries = payload.get("standards")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Registro precisa conter candidatos normativos.")
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Cada candidato normativo precisa ser um objeto.")
        identifier = entry.get("id")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in seen:
            raise ValueError("Identificador normativo vazio ou duplicado.")
        seen.add(identifier)
        for field in ("designation", "edition", "catalog_status", "source_url",
                      "catalog_checked_at", "status_evidence", "criteria_reviewed",
                      "evaluator_id", "applicability_rule_id"):
            if field not in entry:
                raise ValueError(f"Metadado obrigatório ausente: {field}.")
        parsed = urlparse(str(entry["source_url"]))
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"Fonte normativa não é HTTPS: {identifier}.")
        try:
            checked_at = date.fromisoformat(entry["catalog_checked_at"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Data de catálogo inválida: {identifier}.") from exc
        if checked_at > today:
            raise ValueError(f"Data futura de consulta ao catálogo: {identifier}.")
        interval = int(entry.get("review_interval_days", 365))
        if interval < 1 or (today - checked_at).days > interval:
            raise ValueError(f"Consulta ao catálogo desatualizada: {identifier}.")
        if entry["catalog_status"] not in _ALLOWED_STATUSES:
            raise ValueError(f"Status de catálogo não reconhecido: {identifier}.")
        if not isinstance(entry["status_evidence"], str) or not entry["status_evidence"].strip():
            raise ValueError(f"Evidência de status ausente: {identifier}.")
        if entry["criteria_reviewed"]:
            if (not entry.get("lawful_text_access_confirmed")
                    or not entry.get("criteria_reference")
                    or not entry.get("criteria_reviewer")
                    or not entry.get("evaluator_id")):
                raise ValueError(
                    f"Critério sem fonte autorizada, referência, revisão ou avaliador: {identifier}.")


def load_registry(path: str | Path | None = None) -> dict:
    target = Path(path) if path is not None else _REGISTRY_PATH
    payload = json.loads(target.read_text(encoding="utf-8"))
    validate_registry(payload)
    return deepcopy(payload)


def load_requirement_records(path: str | Path | None = None) -> tuple[RequirementRecord, ...]:
    """Convert catalogue entries to fail-closed records; no criteria are inferred."""
    entries = load_registry(path)["standards"]
    return tuple(RequirementRecord(
        requirement_id=item["id"],
        standard=item["designation"],
        edition=item["edition"],
        catalog_status=item["catalog_status"],
        source_url=item["source_url"],
        catalog_checked_at=date.fromisoformat(item["catalog_checked_at"]),
        applicability_rule_id=item["applicability_rule_id"],
        evaluator_id=item["evaluator_id"],
        applicability_description=item.get("applicability_description", ""),
        limitations=tuple(item.get("limitations", ())),
        review_interval_days=int(item.get("review_interval_days", 365)),
    ) for item in entries)
