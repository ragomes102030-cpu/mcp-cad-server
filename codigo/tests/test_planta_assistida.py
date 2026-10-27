from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "codigo" / "src"))

from cad_mcp.planta_assistida import build_assisted_model
from cad_mcp.validar_modelo import validar
from cad_mcp import tools
from cad_mcp.autocad_launcher import start_autocad


def test_default_program_builds_a_valid_floor_plan_from_zero():
    model = build_assisted_model({})
    result = validar(model)

    assert result["ok"] is True
    assert len(model["ambientes"]) == 10
    assert model["espessura_parede"] == 0.15
    assert model["pe_direito"] == 2.8
    assert result["area_util"] == 120.675
    assert len(model["paredes"]) > 20
    assert len(model["portas"]) == 11
    assert len(model["selo"]) == 6


def test_unknown_room_is_rejected_before_drawing():
    try:
        build_assisted_model({"ambientes": ["Garagem"]})
    except ValueError as exc:
        assert "Garagem" in str(exc)
    else:
        raise AssertionError("unknown room was accepted")


def test_assisted_tool_is_registered_with_a_stable_public_name():
    assert tools.planta_assistida in tools.TOOLS
    assert tools.nome_publico(tools.planta_assistida) == "planta_assistida"
    assert tools.planta_criar_validada in tools.TOOLS
    assert tools.nome_publico(tools.planta_criar_validada) == "planta_criar_validada"


def test_local_safe_profile_contains_validated_workflow():
    assert tools.planta_criar_validada in tools.PUBLIC_TOOLS
    assert tools.draw_rectangle not in tools.PUBLIC_TOOLS


def test_template_catalog_is_registered_and_explains_supported_workflows():
    import asyncio

    assert tools.planta_templates in tools.TOOLS
    result = asyncio.run(tools.planta_templates())

    assert result["ok"] is True
    assert result["template_padrao"] == "residencia_unifamiliar_12x11"
    assert {item["id"] for item in result["templates"]} >= {
        "residencia_unifamiliar_12x11", "tiny_house_10m2"
    }


def test_unsupported_dimensions_are_rejected_with_template_guidance():
    import asyncio

    result = asyncio.run(tools.planta_assistida({
        "largura_externa": 2.5,
        "profundidade_externa": 4.0,
        "area_util_minima": 10,
    }, modo="preview"))

    assert result["ok"] is False
    assert result["code"] == "TEMPLATE_NOT_SUPPORTED"
    assert result["templates"]
    assert result["proxima_acao"] == "escolher um template suportado"


def test_tiny_house_template_preview_is_validated_before_drawing():
    import asyncio

    result = asyncio.run(tools.planta_assistida({
        "template": "tiny_house_10m2",
    }, modo="preview"))

    assert result["ok"] is True
    assert result["resumo"]["area_util"] == 8.695
    assert result["resumo"]["ambientes"] == 2
    assert result["validacao"]["ok"] is True


def test_preview_does_not_require_autocad_or_touch_a_drawing():
    import asyncio

    result = asyncio.run(tools.planta_assistida({}, modo="preview"))

    assert result["ok"] is True
    assert result["etapa"] == "preview"
    assert result["proxima_acao"] == "desenhar"
    assert result["preview_token"]


def test_draw_mode_requires_a_preview_token_before_touching_autocad(monkeypatch):
    import asyncio

    async def must_not_start_backend(*_args, **_kwargs):
        raise AssertionError("o backend nao deveria ser chamado sem preview aprovado")

    monkeypatch.setattr(tools, "_obter_backend_autocad", must_not_start_backend)
    result = asyncio.run(tools.planta_assistida({}, modo="desenhar", abrir_autocad=False))

    assert result["ok"] is False
    assert result["code"] == "WORKFLOW_REQUIRED"
    assert result["proxima_acao"] == "chamar planta_assistida(modo='preview')"


def test_draw_mode_refuses_non_com_backend(monkeypatch):
    import asyncio

    class HeadlessBackend:
        name = "ezdxf"

    async def fake_get():
        return HeadlessBackend()

    monkeypatch.setattr(tools.MANAGER, "get", fake_get)
    preview = asyncio.run(tools.planta_assistida({}, modo="preview"))
    result = asyncio.run(tools.planta_assistida(
        {}, modo="desenhar", abrir_autocad=False,
        preview_token=preview["preview_token"],
    ))

    assert result["ok"] is False
    assert result["code"] == "AUTOCAD_REQUIRED"


def test_launcher_starts_the_requested_autocad_executable(monkeypatch, tmp_path):
    import cad_mcp.autocad_launcher as launcher

    executable = tmp_path / "acad.exe"
    executable.write_bytes(b"test")
    calls = []

    class FakeProcess:
        pid = 1234

    def fake_popen(command, **kwargs):
        calls.append((command, kwargs))
        return FakeProcess()

    monkeypatch.setattr(launcher.subprocess, "Popen", fake_popen)
    result = start_autocad(str(executable))

    assert result["ok"] is True
    assert result["pid"] == 1234
    assert calls[0][0] == [str(executable), "/nologo"]


def test_draw_preflight_launches_autocad_and_waits_for_com(monkeypatch):
    import asyncio
    import cad_mcp.autocad_launcher as launcher

    class ComBackend:
        name = "autocad_com"

    attempts = {"get": 0, "start": 0}

    async def fake_get():
        attempts["get"] += 1
        if attempts["get"] == 1:
            raise RuntimeError("COM ainda não está pronto")
        return ComBackend()

    async def fake_reset():
        return None

    def fake_start():
        attempts["start"] += 1
        return {"ok": True, "pid": 9876, "executable": "acad.exe"}

    monkeypatch.setattr(tools, "_b", fake_get)
    monkeypatch.setattr(tools, "_autocad_window_exists", lambda: False)
    monkeypatch.setattr(tools.MANAGER, "reset", fake_reset)
    monkeypatch.setattr(launcher, "start_autocad", fake_start)

    backend, status = asyncio.run(tools._obter_backend_autocad(True, 10))

    assert backend.name == "autocad_com"
    assert status["code"] == "AUTOCAD_READY"
    assert status["iniciado"]["pid"] == 9876
    assert attempts["start"] == 1
