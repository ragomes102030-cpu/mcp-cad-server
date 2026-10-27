# -*- coding: utf-8 -*-
"""Seleção e ciclo de vida do backend CAD.

- mode=auto    -> COM/ActiveX (AutoCAD já aberto); ezdxf headless se o AutoCAD não estiver aberto
- mode=com     -> exige COM com um desenho aberto
- mode=autocad -> exige AutoCAD: tenta COM e, se falhar, a ponte LISP por arquivo
- mode=file_ipc-> ponte LISP por arquivo (AutoCAD LT), exige o dispatcher carregado
- mode=ezdxf   -> sempre headless (não precisa de AutoCAD nem licença)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from .build_identity import revision

# o pacote vendorizado mora em src/autocad_mcp
_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from autocad_mcp.backends.ezdxf_backend import EzdxfBackend  # noqa: E402


def _com_erro(e) -> str:
    """Mensagem curta e legível de um erro de COM (sem stack gigante)."""
    if e is None:
        return "erro desconhecido"
    txt = str(e) or e.__class__.__name__
    return " ".join(txt.split())[:240]


FileIPCBackend = None
find_autocad_window = None
try:  # só existe no Windows e com pywin32 instalado
    from autocad_mcp.backends.file_ipc import FileIPCBackend, find_autocad_window  # noqa: E402
except Exception:  # pragma: no cover
    pass


class BackendManager:
    """Mantém um backend único, inicializado sob demanda."""

    def __init__(self, mode: str | None = None) -> None:
        self.mode = (mode or os.getenv("CAD_MCP_BACKEND") or os.getenv("MCP_CAD_BACKEND", "auto")).lower()
        if self.mode not in {"auto", "com", "autocad", "file_ipc", "ezdxf"}:
            raise ValueError("backend invalido: %s" % self.mode)
        self._backend = None

    # ------------------------------------------------------------------
    def _resolve(self):
        if self.mode == "ezdxf":
            return EzdxfBackend(), "ezdxf (forçado)"

        # 1) COM/ActiveX: motor preferido quando o AutoCAD esta aberto.
        #    Nao rouba foco, nao depende de janela nem de PostMessage.
        erro_com = None
        if self.mode in ("auto", "com", "autocad"):
            try:
                from .com_backend import ComBackend

                b = ComBackend()
                b._conectar(tentativas=2)
                return b, "com (AutoCAD já aberto)"
            except Exception as e:
                erro_com = e
                if self.mode == "com":
                    raise RuntimeError("backend COM indisponível: %s" % e)

        # 2) Ponte LISP por arquivo (funciona no AutoCAD LT, exige a janela visivel
        #    E o dispatcher LISP carregado). So entra quando pedida explicitamente.
        if self.mode in ("autocad", "file_ipc") and FileIPCBackend is not None:
            from . import win32_bridge

            win32_bridge.patch_vendored()
            hwnd = win32_bridge.find_autocad_window()
            if hwnd:
                return FileIPCBackend(), f"file_ipc (AutoCAD hwnd={hwnd})"

        # No modo auto, AutoCAD aberto + COM falhando = quase sempre "tela inicial"
        # (nenhum desenho aberto). Escolher file_ipc aqui esconderia o problema e
        # faria TODA chamada estourar em timeout; melhor falhar com o motivo.
        if self.mode == "auto" and FileIPCBackend is not None:
            try:
                from . import win32_bridge

                hwnd = win32_bridge.find_autocad_window()
            except Exception:
                hwnd = None
            if hwnd:
                raise RuntimeError(
                    "AutoCAD esta aberto mas nao respondeu via COM (%s). "
                    "Abra um desenho (nao deixe o AutoCAD na tela inicial) e tente de novo. "
                    "Para usar a ponte por arquivo, suba com CAD_MCP_BACKEND=file_ipc "
                    "e o dispatcher LISP carregado." % _com_erro(erro_com)
                )

        if self.mode == "autocad":
            raise RuntimeError(
                "AutoCAD nao encontrado: nem via COM (GetActiveObject) nem por janela. "
                "Abra o AutoCAD uma vez e tente de novo."
            )
        return EzdxfBackend(), "ezdxf (headless, sem AutoCAD aberto)"

    async def get(self):
        if self._backend is None:
            backend, motivo = self._resolve()
            initialized = await backend.initialize()
            if not initialized.ok:
                raise RuntimeError(initialized.error or "falha na inicializacao do backend")
            self._backend, self._motivo = backend, motivo
        return self._backend

    async def status(self) -> dict:
        try:
            b = await self.get()
            st = await b.status()
            return {
                "ok": st.ok,
                "backend": b.name,
                "selecao": getattr(self, "_motivo", "?"),
                "modo_configurado": self.mode,
                "capabilities": vars(b.capabilities),
                "status": st.to_dict(),
                "build": {"version": __import__("cad_mcp").__version__,
                          "revision": revision(),
                          "transport": "stdio",
                          "backend": "autocad-or-headless"},
                "codigo": {"source": str(Path(__file__).resolve())},
            }
        except Exception as e:
            return {
                "ok": False,
                "backend": None,
                "modo_configurado": self.mode,
                "erro": _com_erro(e),
                "dica": ("Abra um desenho no AutoCAD e aguarde a tela inicial terminar; "
                         "depois reconecte o MCP. Se usar AutoCAD LT, configure "
                         "CAD_MCP_BACKEND=file_ipc e carregue o dispatcher LISP."),
            }

    async def reset(self) -> None:
        self._backend = None


MANAGER = BackendManager()
