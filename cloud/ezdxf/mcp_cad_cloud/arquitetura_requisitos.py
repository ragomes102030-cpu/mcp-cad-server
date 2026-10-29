"""Contracts for traceable architectural requirement evaluation.

This module deliberately does not encode building-code or NBR criteria.
Requirements without verified source metadata and a registered evaluator stay
not testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Callable, Mapping
from urllib.parse import urlparse


class RequirementStatus(str, Enum):
    PASSED = "passou"
    FAILED = "falhou"
    NOT_TESTABLE = "não testável"
    NOT_APPLICABLE = "não aplicável"


@dataclass(frozen=True)
class ProjectContext:
    project_name: str
    use: str
    typology: str
    municipality: str | None
    state: str | None
    storeys: int
    lot_width_m: float | None
    lot_depth_m: float | None
    requested_rooms: tuple[str, ...]
    stage: str
    municipal_profile_revision: str | None = None


@dataclass(frozen=True)
class RequirementRecord:
    requirement_id: str
    standard: str
    edition: str
    catalog_status: str
    source_url: str
    catalog_checked_at: date
    applicability_rule_id: str
    evaluator_id: str | None
    applicability_description: str = ""
    limitations: tuple[str, ...] = ()
    review_interval_days: int = 365


@dataclass(frozen=True)
class MunicipalProfile:
    schema_version: int
    municipality: str
    state: str
    source_url: str
    retrieved_at: date
    revision: str
    reviewer: str
    review_interval_days: int = 365


@dataclass(frozen=True)
class RequirementResult:
    requirement_id: str
    status: RequirementStatus
    reason: str
    evidence: tuple[str, ...] = ()
    standard: str = ""
    edition: str = ""


ApplicabilityRule = Callable[[ProjectContext], bool | None]
RequirementEvaluator = Callable[[ProjectContext], tuple[bool, str, tuple[str, ...]]]


def _https_source(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def evaluate_applicability(
    project: ProjectContext,
    requirement: RequirementRecord,
    *,
    applicability_rules: Mapping[str, ApplicabilityRule],
    evaluators: Mapping[str, RequirementEvaluator],
    as_of: date | None = None,
) -> RequirementResult:
    """Evaluate one requirement and fail closed when source/context is weak."""
    today = as_of or date.today()

    def not_testable(reason: str) -> RequirementResult:
        return RequirementResult(
            requirement.requirement_id,
            RequirementStatus.NOT_TESTABLE,
            reason,
            standard=requirement.standard,
            edition=requirement.edition,
        )

    if not requirement.requirement_id.strip():
        return not_testable("Identificador do requisito ausente.")
    if not requirement.standard.strip() or not requirement.edition.strip():
        return not_testable("Norma ou edição não identificada.")
    if not _https_source(requirement.source_url):
        return not_testable("Fonte HTTPS verificável não informada.")
    if requirement.catalog_status.strip().casefold() != "em vigor":
        return not_testable("Status da edição não está confirmado como em vigor.")
    if requirement.review_interval_days < 1:
        return not_testable("Intervalo de revisão do catálogo inválido.")
    age_days = (today - requirement.catalog_checked_at).days
    if age_days < 0 or age_days > requirement.review_interval_days:
        return not_testable("Consulta ao catálogo está desatualizada; revise a edição e o status.")

    rule = applicability_rules.get(requirement.applicability_rule_id)
    if rule is None:
        return not_testable("Regra de aplicabilidade não registrada.")
    applicability = rule(project)
    if applicability is None:
        return not_testable("Dados do projeto ou perfil municipal insuficientes para determinar a aplicabilidade.")
    if applicability is False:
        return RequirementResult(
            requirement.requirement_id,
            RequirementStatus.NOT_APPLICABLE,
            "Requisito não aplicável a este contexto de projeto.",
            standard=requirement.standard,
            edition=requirement.edition,
        )

    if not requirement.evaluator_id or requirement.evaluator_id not in evaluators:
        return not_testable("Verificador independente não registrado para este requisito.")
    passed, reason, evidence = evaluators[requirement.evaluator_id](project)
    if not reason.strip():
        return not_testable("Verificador não informou justificativa para o resultado.")
    normalized_evidence = tuple(item for item in evidence if isinstance(item, str) and item.strip())
    if passed and not normalized_evidence:
        return not_testable("Verificador aprovou sem apontar evidência rastreável.")

    return RequirementResult(
        requirement.requirement_id,
        RequirementStatus.PASSED if passed else RequirementStatus.FAILED,
        reason,
        normalized_evidence,
        requirement.standard,
        requirement.edition,
    )


def validate_municipal_profile(
    profile: MunicipalProfile,
    project: ProjectContext,
    *,
    as_of: date | None = None,
) -> tuple[str, ...]:
    """Return profile defects; an empty tuple means metadata is reviewable."""
    today = as_of or date.today()
    errors: list[str] = []
    if profile.schema_version != 1:
        errors.append("Versão do esquema municipal não suportada.")
    if not profile.municipality.strip() or not profile.state.strip():
        errors.append("Município e UF são obrigatórios.")
    if not _https_source(profile.source_url):
        errors.append("Perfil municipal precisa de fonte oficial HTTPS.")
    if not profile.revision.strip():
        errors.append("Revisão do perfil municipal ausente.")
    if not profile.reviewer.strip():
        errors.append("Perfil municipal ainda não revisado.")
    if profile.review_interval_days < 1:
        errors.append("Intervalo de revisão municipal inválido.")
    age_days = (today - profile.retrieved_at).days
    if age_days < 0 or age_days > profile.review_interval_days:
        errors.append("Fonte municipal desatualizada; revisar a legislação e o perfil.")
    if project.municipality is None or project.state is None:
        errors.append("Município/UF do projeto não informados.")
    elif (profile.municipality.strip().casefold() != project.municipality.strip().casefold()
          or profile.state.strip().casefold() != project.state.strip().casefold()):
        errors.append("Perfil municipal não corresponde ao município/UF do projeto.")
    if (project.municipal_profile_revision is None
            or profile.revision != project.municipal_profile_revision):
        errors.append("Revisão do perfil não corresponde ao contexto do projeto.")
    return tuple(errors)
