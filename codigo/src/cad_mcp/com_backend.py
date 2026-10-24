# -*- coding: utf-8 -*-
"""Backend AutoCAD via COM/ActiveX — o motor "vivo" principal do mcp-cad-server.

Por que COM e nao PostMessage/arquivo?
    O truque de injetar WM_CHAR no MDIClient depende do layout da janela de
    linha de comando (que no AutoCAD 2025 nem e' filha do MDIClient) e rouba
    foco. `Document.SendCommand` faz o mesmo pelo canal oficial de automacao:
      - nao rouba foco (funciona com o AutoCAD minimizado);
      - nao depende de versao nem do LT;
      - `PlotToFile` resolve o PDF nativamente.

Licoes aprendidas (custaram caro, ficam registradas):
  1. NUNCA usar `(load "arquivo.lsp")`: o SECURELOAD do AutoCAD abre um
     dialogo modal "Security - Unsigned Executable File" e o dialogo modal
     bloqueia TODAS as chamadas COM (RPC_E_CALL_REJECTED). Por isso o codigo
     LISP vai INLINE, montado como string e rodado com `(eval (read ...))`.
  2. `SendCommand` e' assincrono e a linha de comando aceita strings longas
     (testado com >500 chars), mas o texto TEM que terminar com "\n",
     senao o AutoCAD fica esperando Enter e passa a rejeitar o COM.
  3. AutoCAD rejeita chamadas COM de vez em quando enquanto esta ocupado
     (`RPC_E_CALL_REJECTED`). Todo acesso passa por `_chamar`, que tenta de
     novo com backoff e, se preciso, manda um ESC para limpar o prompt.
  4. `Application.Documents` as vezes volta sem type-info (binding tardio);
     o caminho confiavel e' `Application.ActiveDocument`.
  5. Para achar o desenho atual, `ActiveDocument.ModelSpace.Count` funciona
     sempre; `Documents.Count` nao.

Nada e' escrito no perfil do usuario: nem acaddoc.lsp, nem SECURELOAD,
nem TRUSTEDPATHS. Os temporarios ficam em %MCP_CAD_TEMP% (padrao
C:/temp/mcp_cad_com, sem espacos).
"""
from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from autocad_mcp.backends.base import (  # noqa: E402
    AutoCADBackend,
    BackendCapabilities,
    CommandResult,
)

from .sexp import parse as sexp_parse  # noqa: E402

# --------------------------------------------------------------- constantes COM
AC_EXTENTS = 1
AC_SCALE_TO_FIT = 0
PLOTTER_PDF = "DWG To PDF.pc3"

# candidatos de FileType para DXF no SaveAs (mudam entre versoes; testamos)
DXF_SAVEAS_TYPES = (65, 61, 33, 29, 25, 21, 17, 13, 1)

PROGIDS = ("AutoCAD.Application.25", "AutoCAD.Application.24", "AutoCAD.Application")

# HRESULTs de "servidor ocupado" -> vale tentar de novo
BUSY = (-2147418111, -2147417846, -2147417847)
TENTATIVAS = int(os.environ.get("MCP_CAD_COM_TENTATIVAS", "16"))


def _q(s) -> str:
    """Escapa uma string Python para virar literal AutoLISP."""
    return str(s).replace("\\", "/").replace('"', '\\"')


def _uma_linha(texto: str) -> str:
    """Normaliza o codigo LISP para UMA linha, sem mexer dentro de strings.

    `SendCommand` interpreta "\\n" como Enter, entao quebra de linha no meio de
    um `progn` vira prompt de continuacao (ruido). Espaco dentro de literal e'
    permitido; fora dele colapsamos para um unico espaco.
    """
    saida = []
    dentro = False
    escape = False
    pendente = False
    for c in texto:
        if dentro:
            if escape:
                saida.append(c)
                escape = False
                continue
            if c == "\\":
                saida.append(c)
                escape = True
                continue
            if c == '"':
                saida.append(c)
                dentro = False
                continue
            saida.append(" " if c in "\r\n\t" else c)
            continue
        if c in " \t\r\n":
            pendente = True
            continue
        if c == ";":
            # estamos numa linha unica: um comentario comeria o resto do programa
            return "".join(saida)
        if c == '"':
            if pendente and saida:
                saida.append(" ")
            pendente = False
            saida.append(c)
            dentro = True
            continue
        if pendente and saida:
            saida.append(" ")
        pendente = False
        saida.append(c)
    return "".join(saida)


def _com_erro(e: Exception) -> str:
    txt = str(e)
    low = txt.lower()
    if "rejeitada" in low or "rejected" in low:
        return "AutoCAD ocupado (RPC_E_CALL_REJECTED): %s" % txt
    return txt


class ComBackend(AutoCADBackend):
    """Backend que conversa com um AutoCAD JA ABERTO pelo canal COM."""

    name = "autocad_com"

    def __init__(self) -> None:
        self._app = None
        self._doc = None
        self._tid: int | None = None
        base = os.environ.get("MCP_CAD_TEMP") or "C:/temp/mcp_cad_com"
        self._raiz = Path(base)
        try:
            self._raiz.mkdir(parents=True, exist_ok=True)
        except Exception:
            self._raiz = Path(tempfile.gettempdir()) / "mcp_cad_com"
            self._raiz.mkdir(parents=True, exist_ok=True)
        self._contador = 0

    # ------------------------------------------------------------- propriedades
    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            can_read_drawing=True,
            can_modify_entities=True,
            can_create_entities=True,
            can_screenshot=True,
            can_save=True,
            can_plot_pdf=True,
            can_zoom=True,
            can_query_entities=True,
            can_file_operations=True,
            can_undo=True,
        )

    # ---------------------------------------------------------------- retry/COM
    def _esc(self) -> None:
        """Manda ESC de verdade para limpar um prompt pendente do AutoCAD.

        Sem isso o AutoCAD recusa as chamadas COM em loop (o agente via isso como
        'COM caiu') e cada retry espera 1,5 s.
        """
        try:
            from . import win32_bridge

            h = win32_bridge.find_autocad_window()
            if h:
                win32_bridge.enviar_esc(h, forcado=True)
        except Exception:
            pass

    def _chamar(self, fn, *a, **kw):
        """Executa um acesso COM tolerando 'AutoCAD ocupado'."""
        atraso = 0.2
        ultimo = None
        for i in range(TENTATIVAS):
            try:
                return fn(*a, **kw)
            except Exception as e:
                ultimo = e
                code = getattr(e, "hresult", None)
                if code not in BUSY:
                    raise
                if i and i % 4 == 0:
                    self._esc()
                time.sleep(atraso)
                atraso = min(atraso * 1.3, 1.5)
        raise RuntimeError("AutoCAD recusou a chamada COM %d vezes: %s" % (TENTATIVAS, _com_erro(ultimo)))

    def _coinit(self) -> None:
        """pywin32/COM exige CoInitialize por thread."""
        tid = threading.get_ident()
        if self._tid != tid:
            try:
                import pythoncom

                pythoncom.CoInitialize()
            except Exception:
                pass
            self._tid = tid
            self._app = None
            self._doc = None

    def _conectar(self, tentativas: int | None = None) -> None:
        self._coinit()
        if self._app is not None and self._doc is not None:
            try:
                self._chamar(lambda: self._doc.Name)
                return
            except Exception:
                self._app = self._doc = None

        import win32com.client as wc

        ultimo = None
        for progid in PROGIDS:
            try:
                self._app = self._chamar(wc.GetActiveObject, progid)
                break
            except Exception as e:
                ultimo = e
                self._app = None
        if self._app is None:
            raise RuntimeError(
                "AutoCAD nao exposto via COM (GetActiveObject falhou). "
                "Abra o AutoCAD normalmente e tente de novo. Ultimo erro: %s" % _com_erro(ultimo)
            )
        try:
            self._doc = self._chamar(lambda: self._app.ActiveDocument)
        except Exception:
            self._doc = None
        if self._doc is None:
            # AutoCAD pode estar na tela inicial (Start), sem nenhum desenho:
            # GetActiveObject funciona, mas ActiveDocument levanta erro.
            # Cria um desenho novo em vez de derrubar o backend inteiro.
            for _ in range(3):
                try:
                    self._doc = self._chamar(self._app.Documents.Add)
                    if self._doc is not None:
                        break
                except Exception as e:
                    ultimo = e
                    time.sleep(0.4)
        if self._doc is None:
            raise RuntimeError(
                "AutoCAD sem documento ativo e nao foi possivel criar um "
                "(Documents.Add falhou: %s). Abra um desenho e tente de novo." % _com_erro(ultimo)
            )

    def _d(self):
        self._conectar()
        return self._doc

    # -------------------------------------------------------------- primitivas
    def _send(self, texto: str) -> None:
        """Manda texto para a linha de comando (garante o Enter no fim).

        O LISP (handent, ssget, entmakex) SEMPRE roda no documento ATIVO do AutoCAD,
        nao no documento que o backend guardou. Se o usuario (ou uma chamada COM)
        trocar a janela ativa, o SendCommand cairia no desenho errado e o handent
        devolveria nil. Por isso ativamos o documento alvo antes de cada envio.
        """
        doc = self._d()
        try:
            ativo = self._chamar(lambda: self._app.ActiveDocument.Name)
            alvo = self._chamar(lambda: doc.Name)
            if ativo != alvo:
                self._chamar(doc.Activate)
                time.sleep(0.15)
        except Exception:
            pass
        if not texto.endswith("\n"):
            texto += "\n"
        self._chamar(doc.SendCommand, texto)

    def _novo_arquivo(self, prefixo: str, ext: str) -> Path:
        self._contador += 1
        return self._raiz / ("%s_%03d_%s.%s" % (prefixo, self._contador, uuid.uuid4().hex[:6], ext))

    def _eval_lines(self, expr: str, timeout: float = 30.0) -> tuple[bool, list[str], str | None]:
        """Roda `expr` no AutoCAD (INLINE, sem `load`) e devolve as linhas de saida."""
        res = self._novo_arquivo("out", "txt")
        res_posix = str(res).replace("\\", "/")
        linha = _uma_linha(expr)
        programa = (
            '(progn (setq __mcp_r (vl-catch-all-apply (quote (lambda () %s))))'
            ' (setq __mcp_f (open "%s" "w"))'
            ' (if (vl-catch-all-error-p __mcp_r)'
            '  (progn (write-line "MCPERR" __mcp_f)'
            '         (write-line (vl-catch-all-error-message __mcp_r) __mcp_f))'
            '  (write-line (vl-prin1-to-string __mcp_r) __mcp_f))'
            ' (close __mcp_f) (princ))'
        ) % (linha, res_posix)
        self._send(programa)

        t0 = time.time()
        while time.time() - t0 < timeout:
            if res.exists():
                time.sleep(0.05)
                try:
                    linhas = res.read_text(encoding="utf-8", errors="replace").splitlines()
                except Exception:
                    linhas = []
                if linhas and linhas[0] == "MCPERR":
                    return False, linhas, (linhas[1] if len(linhas) > 1 else "erro LISP")
                return True, linhas, None
            time.sleep(0.04)
        return False, [], "timeout de %.1fs (AutoCAD sem executar o SendCommand)" % timeout

    def _eval(self, expr: str, timeout: float = 30.0):
        ok, linhas, erro = self._eval_lines(expr, timeout)
        if not ok:
            raise RuntimeError(erro)
        if not linhas:
            return None
        return sexp_parse(linhas[0])

    def _aval(self, expr: str, timeout: float = 30.0) -> CommandResult:
        try:
            valor = self._eval(expr, timeout)
        except Exception as e:
            return CommandResult(ok=False, error=str(e))
        # BricsCAD/AutoCAD nao tem (error "...") disponivel em todo contexto
        # ("no function definition: ERROR"), entao o LISP sinaliza falha
        # devolvendo a string "MCPERRO:<mensagem>".
        if isinstance(valor, str) and valor.startswith("MCPERRO:"):
            return CommandResult(ok=False, error=valor[len("MCPERRO:"):])
        return CommandResult(ok=True, payload=valor)

    # ------------------------------------------------------------------ ciclo
    async def initialize(self) -> CommandResult:
        try:
            self._conectar()
            doc = self._d()
            info = {"backend": self.name, "documento": self._chamar(lambda: doc.Name)}
            try:
                info["aplicacao"] = self._chamar(lambda: self._app.Name)
                info["versao"] = self._chamar(lambda: self._app.Version)
            except Exception:
                pass
            # ambiente previsivel para desenhar/cotar (NAO mexe em SECURELOAD)
            for var, val in (("CMDECHO", 0), ("OSMODE", 0), ("ATTDIA", 0), ("MIRRTEXT", 0)):
                try:
                    self._chamar(doc.SetVariable, var, val)
                except Exception:
                    pass
            return CommandResult(ok=True, payload=info)
        except Exception as e:
            return CommandResult(ok=False, error=_com_erro(e))

    async def status(self) -> CommandResult:
        try:
            self._conectar()
            return CommandResult(
                ok=True,
                payload={
                    "backend": self.name,
                    "documento": self._chamar(lambda: self._doc.Name),
                    "pronto": True,
                },
            )
        except Exception as e:
            return CommandResult(ok=False, error=_com_erro(e))

    # ------------------------------------------------------------ desenho (info)
    async def drawing_info(self) -> CommandResult:
        expr = (
            '(progn (setq __d (vla-get-ActiveDocument (vlax-get-acad-object)))'
            ' (list (cons (quote nome) (vla-get-Name __d))'
            ' (cons (quote caminho) (vla-get-FullName __d))'
            ' (cons (quote salvo) (if (= (vla-get-Saved __d) :vlax-true) 1 0))'
            ' (cons (quote entidades) (vla-get-Count (vla-get-ModelSpace __d)))'
            ' (cons (quote camadas) (vla-get-Count (vla-get-Layers __d)))'
            ' (cons (quote layouts) (vla-get-Count (vla-get-Layouts __d)))'
            ' (cons (quote limites) (list (getvar "LIMMIN") (getvar "LIMMAX")))'
            ' (cons (quote unidade) (getvar "INSUNITS"))))'
        )
        return self._aval(expr)

    async def drawing_get_variables(self, names: list[str] | None = None) -> CommandResult:
        if not names:
            names = ["DIMSCALE", "DIMTXT", "DIMASZ", "CLAYER", "LTSCALE", "INSUNITS", "MEASUREMENT", "TEXTSIZE"]
        pares = " ".join('(cons "%s" (getvar "%s"))' % (n, n) for n in names)
        return self._aval("(list %s)" % pares)

    async def entity_count(self, layer: str | None = None) -> CommandResult:
        if layer:
            expr = '(sslength (ssget "_X" (list (cons 8 "%s"))))' % _q(layer)
        else:
            expr = '(vla-get-Count (vla-get-ModelSpace (vla-get-ActiveDocument (vlax-get-acad-object))))'
        return self._aval(expr)

    async def layer_list(self) -> CommandResult:
        expr = (
            '(progn (vl-load-com) (setq __d (vla-get-ActiveDocument (vlax-get-acad-object)))'
            ' (setq __out "")'
            ' (vlax-for __l (vla-get-Layers __d)'
            '   (setq __out (strcat __out (vla-get-Name __l) "|"'
            '     (itoa (vla-get-Color __l)) "|" (vla-get-Linetype __l) "|"'
            '     (if (= (vla-get-LayerOn __l) :vlax-true) "1" "0") "|"'
            '     (if (= (vla-get-Freeze __l) :vlax-true) "1" "0") "|"'
            '     (if (= (vla-get-Lock __l) :vlax-true) "1" "0") "|"'
            '     (if (= (vla-get-Plottable __l) :vlax-true) "1" "0") "\\n")))'
            ' __out)'
        )
        try:
            bruto = self._eval(expr)
        except Exception as e:
            return CommandResult(ok=False, error=str(e))
        camadas = []
        if isinstance(bruto, str):
            for linha in bruto.split("\n"):
                p = linha.split("|")
                if len(p) >= 7:
                    camadas.append({
                        "nome": p[0],
                        "cor": int(p[1]) if p[1].lstrip("-").isdigit() else p[1],
                        "linetype": p[2],
                        "ligada": p[3] == "1",
                        "congelada": p[4] == "1",
                        "travada": p[5] == "1",
                        "plota": p[6] == "1",
                    })
        return CommandResult(ok=True, payload=camadas)

    async def block_list(self) -> CommandResult:
        return CommandResult(ok=True, payload=[])

    # -------------------------------------------------------------- arquivo
    def _doc_aberto(self, caminho: str):
        """Devolve o Document que ja' esta aberto com esse caminho, ou None.

        Serve para nao repetir o erro classico: Documents.Add cria "Drawing9",
        o SaveAs para um arquivo JA' ABERTO falha e o tool dizia ok mesmo assim.
        """
        alvo = os.path.normcase(os.path.abspath(caminho))
        try:
            total = self._chamar(lambda: self._app.Documents.Count)
        except Exception:
            return None
        for i in range(total):
            try:
                d = self._chamar(self._app.Documents.Item, i)
                cheio = self._chamar(lambda: d.FullName) or ""
            except Exception:
                continue
            if cheio and os.path.normcase(os.path.abspath(cheio)) == alvo:
                return d
        return None

    async def drawing_create(self, name: str | None = None) -> CommandResult:
        try:
            self._conectar()
            if not name:
                novo = self._chamar(self._app.Documents.Add)
                self._doc = novo
                return CommandResult(ok=True, payload={"documento": self._chamar(lambda: novo.Name),
                                                       "reutilizado": False})
            alvo = Path(os.path.abspath(name))
            alvo.parent.mkdir(parents=True, exist_ok=True)
            aberto = self._doc_aberto(str(alvo))
            if aberto is not None:
                # Ja' esta aberto (inclusive por um teste anterior): reaproveita.
                self._doc = aberto
                try:
                    self._chamar(aberto.Activate)
                except Exception:
                    pass
                return CommandResult(ok=True, payload={"documento": self._chamar(lambda: aberto.Name),
                                                       "caminho": str(alvo), "reutilizado": True})
            novo = self._chamar(self._app.Documents.Add)
            self._doc = novo
            try:
                self._chamar(novo.SaveAs, str(alvo).replace("\\", "/"))
            except Exception as e:
                # Sem este erro explicito o tool devolvia ok=True com "Drawing9".
                return CommandResult(
                    ok=False,
                    error="documento criado como '%s', mas o SaveAs para '%s' falhou: %s"
                          % (self._chamar(lambda: novo.Name), alvo, _com_erro(e)))
            return CommandResult(ok=True, payload={"documento": self._chamar(lambda: novo.Name),
                                                   "caminho": str(alvo), "reutilizado": False})
        except Exception as e:
            return CommandResult(ok=False, error=_com_erro(e))

    async def drawing_setup(self, unidades: int = 6, escala_cota: float = 0.1,
                            ltscale: float = 0.2) -> CommandResult:
        """Ajusta o desenho novo para trabalhar em METROS (INSUNITS=6).

        Sem isso o DXF sai com INSUNITS=mm e o quantitativo interpreta errado.
        `escala_cota` e o DIMSCALE: 0,1 deixa o texto da cota com 0,25 m (5 mm no
        papel a 1:50) e a flecha com 0,10 m (2 mm). Com 1,0 o texto sai 10x maior.
        `ltscale` e o LTSCALE, que NAO e' afetado pelo DIMSCALE: 0,2 com o DASHED do
        acad.lin (padrao 0,5 / -0,25) da' traco de 2 mm e vao de 1 mm no papel a 1:50.
        """
        return self._aval(
            '(progn (setvar "INSUNITS" %d) (setvar "MEASUREMENT" 1)'
            ' (setvar "LUNITS" 2) (setvar "LUPREC" 2) (setvar "AUNITS" 0)'
            ' (setvar "DIMSCALE" %s) (setvar "TEXTSIZE" 0.2)'
            ' (setvar "DIMDEC" 2) (setvar "DIMZIN" 0) (setvar "DIMTAD" 1)'
            # DIMASZ/DIMEXE sao multiplicados pelo DIMSCALE: 1.0 x 0.1 = flecha de
            # 0,10 m (2 mm no papel a 1:50). Nao "corrija" para 0.125 sem mexer no
            # DIMSCALE, senao a flecha fica 10x menor.
            ' (setvar "DIMASZ" 1.0) (setvar "DIMEXE" 0.6) (setvar "DIMEXO" 0.4)'
            # DIMTXT/DIMGAP tambem sao multiplicados pelo DIMSCALE: 2.5 x 0.1 = 0.25 m
            # (5 mm no papel a 1:50) e 0.5 x 0.1 = 0.05 m de afastamento.
            # Estes ficavam HERDANDO o seed do template, e duas rodadas do mesmo prompt
            # saiam com extensoes diferentes so' por causa do texto da cota
            # ("11" x "11,00" muda a largura do DIMENSION e o EXTMIN). Cravados aqui.
            ' (setvar "DIMTXT" 2.5) (setvar "DIMTIH" 0) (setvar "DIMTOH" 0)'
            ' (setvar "DIMGAP" 0.5) (setvar "DIMLUNIT" 2) (setvar "DIMBLK" ".")'
            # LTSCALE nao e' afetado pelo DIMSCALE e o resultado depende do padrao do
            # LTYPE carregado: acad.lin define DASHED como 0,5 / -0,25 e acadiso.lin
            # como 12,7 / -6,35 (25x maior). Com o acad.lin, 1,0 dava traco de 0,5 m
            # (10 mm no papel a 1:50 — grosseiro) e 0,05 dava 0,5 mm (parece
            # CONTINUOUS). 0,2 da' 2 mm de traco / 1 mm de vao no papel a 1:50.
            ' (setvar "LTSCALE" %s) (setvar "PSLTSCALE" 1)'
            ' (setvar "PDMODE" 0) (setvar "MIRRTEXT" 0) (setvar "ATTDIA" 0) T)'
            % (unidades, escala_cota, ltscale)
        )

    async def drawing_open(self, path: str) -> CommandResult:
        try:
            self._conectar()
            p = str(Path(path)).replace("\\", "/")
            d = self._chamar(self._app.Documents.Open, p)
            self._doc = d
            return CommandResult(ok=True, payload={"documento": self._chamar(lambda: d.Name), "caminho": p})
        except Exception as e:
            return CommandResult(ok=False, error=_com_erro(e))

    async def drawing_save(self, path: str | None = None) -> CommandResult:
        try:
            doc = self._d()
            if path:
                alvo = Path(os.path.abspath(path))
                alvo.parent.mkdir(parents=True, exist_ok=True)
                # ATENCAO: "outro is doc" NAO funciona com pywin32 (cada chamada devolve
                # um wrapper novo). Comparar pelo caminho.
                atual = self._chamar(lambda: doc.FullName) or ""
                mesmo = bool(atual) and os.path.normcase(os.path.abspath(atual)) == os.path.normcase(str(alvo))
                if mesmo:
                    self._chamar(doc.Save)
                    if not alvo.exists():
                        return CommandResult(ok=False, error="Save executou mas '%s' nao esta no disco" % alvo)
                    return CommandResult(ok=True, payload={"salvo_em": str(alvo), "bytes": alvo.stat().st_size})
                if self._doc_aberto(str(alvo)) is not None:
                    return CommandResult(
                        ok=False,
                        error="'%s' ja' esta aberto no AutoCAD como outro desenho; feche-o ou salve com outro nome"
                              % alvo)
                # o SaveAs do AutoCAD reclama se o arquivo ja' existe em alguns casos
                if alvo.exists():
                    try:
                        alvo.unlink()
                    except Exception:
                        pass
                self._chamar(doc.SaveAs, str(alvo).replace("\\", "/"))
                if not alvo.exists():
                    return CommandResult(ok=False, error="SaveAs executou mas '%s' nao apareceu no disco" % alvo)
                return CommandResult(ok=True, payload={"salvo_em": str(alvo), "bytes": alvo.stat().st_size})
            if not self._chamar(lambda: doc.FullName):
                return CommandResult(ok=False, error="desenho novo sem caminho: informe 'path'")
            self._chamar(doc.Save)
            return CommandResult(ok=True, payload={"salvo_em": self._chamar(lambda: doc.FullName)})
        except Exception as e:
            return CommandResult(ok=False, error=_com_erro(e))

    def _estagio_sem_espaco(self, sufixo: str) -> Path:
        # Estagios antigos se acumulavam (11 `stage_*.dwg` em C:\temp\mcp_cad_com num
        # dia de teste). Apaga os com mais de 24 h antes de criar o novo; os de hoje
        # ficam, porque podem ser o arquivo de trabalho de um desenho ainda aberto.
        try:
            limite = time.time() - 86400
            for velho in self._raiz.glob("stage_*"):
                try:
                    if velho.stat().st_mtime < limite:
                        velho.unlink()
                except Exception:
                    pass
        except Exception:
            pass
        return self._raiz / ("stage_%s_%s%s" % (uuid.uuid4().hex[:8], time.strftime("%H%M%S"), sufixo))

    async def drawing_save_as_dxf(self, path: str) -> CommandResult:
        """Exporta o desenho atual para DXF.

        Rota preferida: `doc.Export` por COM, direto do desenho NA MEMORIA.
        Isso importa: o `accoreconsole` le o DWG do disco e, se o desenho tem
        alteracoes nao salvas (ou nunca foi salvo), ele converte a versao antiga
        e o DXF sai vazio/desatualizado — foi a causa do "204 entidades no
        AutoCAD e 0 no DXF". O accoreconsole fica como fallback, e o
        `-WBLOCK` por linha de comando nao e' usado porque trava o prompt.
        """
        destino = Path(path)
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        if destino.exists():
            try:
                destino.unlink()
            except Exception:
                pass

        # 1) rota COM: doc.Export com SelectionSet (nao usa comando interativo).
        #    `Export(FileName, Extension, SelectionSet)` ACRESCENTA a extensao ao
        #    FileName, entao passamos o caminho SEM sufixo e movemos o resultado.
        ultimo = "sem rota"
        base = destino
        if base.suffix.lower() == ".dxf":
            base = base.with_suffix("")
        nome_ss = "MCP_EXPORT_DXF"
        try:
            doc = self._d()
            try:
                self._chamar(lambda: doc.SelectionSets.Item(nome_ss).Delete())
            except Exception:
                pass
            ss = self._chamar(doc.SelectionSets.Add, nome_ss)
            try:
                # acSelectionSetAll = 5
                self._chamar(ss.Select, 5)
                self._chamar(doc.Export, str(base).replace("\\", "/"), "DXF", ss)
            finally:
                try:
                    self._chamar(ss.Delete)
                except Exception:
                    pass
            gerado = None
            for ext in (".dxf", ".DXF"):
                cand = Path(str(base) + ext)
                if cand.exists():
                    gerado = cand
                    break
            if gerado:
                if gerado.resolve() != destino.resolve():
                    try:
                        if destino.exists():
                            destino.unlink()
                        os.replace(str(gerado), str(destino))
                    except Exception as e:
                        ultimo = "exportou em '%s' mas nao moveu para '%s': %s" % (
                            gerado, destino, _com_erro(e))
                        gerado = str(gerado)
                if destino.exists() and destino.stat().st_size > 200:
                    return CommandResult(
                        ok=True,
                        payload={"dxf": str(destino), "bytes": destino.stat().st_size,
                                 "rota": "doc.Export"},
                    )
            ultimo = "doc.Export nao gerou o arquivo DXF"
        except Exception as e:
            ultimo = _com_erro(e)

        # 2) accoreconsole: precisa de um DWG em disco (e de um DWG ATUALIZADO)
        try:
            from . import accore

            if accore.disponivel():
                doc = self._d()
                atual = self._chamar(lambda: doc.FullName)
                estagio = None
                aviso = None
                # Desenho nunca salvo: FullName aponta para um arquivo que NAO existe
                # (ex.: ...\Arquimedes\arquimedes\reteste_apto_14x11). Salvamos uma
                # copia de trabalho (o documento ativo passa a apontar para ela).
                if not atual or not os.path.exists(str(atual)):
                    nome_antes = self._chamar(lambda: doc.Name)
                    atual = str(self._estagio_sem_espaco(".dwg"))
                    try:
                        self._chamar(doc.SaveAs, atual.replace("\\", "/"))
                        estagio = nome_antes
                    except Exception as e:
                        ultimo = ("o desenho '%s' nao esta salvo em disco e o SaveAs para "
                                  "'%s' falhou: %s" % (nome_antes, atual, _com_erro(e)))
                        atual = None
                else:
                    # O disco pode estar atrasado em relacao a memoria; salva antes
                    # de converter, senao o DXF volta com o conteudo antigo.
                    try:
                        self._chamar(doc.Save)
                        aviso = ("o desenho foi salvo em '%s' antes de exportar (o "
                                 "accoreconsole le do disco)" % atual)
                    except Exception as e:
                        aviso = ("nao deu para salvar '%s' antes de exportar (%s); o DXF "
                                 "pode sair desatualizado" % (atual, _com_erro(e)))
                if atual:
                    r = accore.dwg_para_dxf(atual, destino)
                    if r.get("ok"):
                        r["rota"] = "accoreconsole"
                        r["origem_dwg"] = atual
                        if estagio:
                            r["aviso"] = ("o desenho '%s' nao estava salvo em disco; salvei uma "
                                          "copia de trabalho em '%s' (o documento ativo passou a "
                                          "apontar para ela) e exportei dela"
                                          % (estagio, atual))
                        elif aviso:
                            r["aviso"] = aviso
                        return CommandResult(ok=True, payload=r)
                    ultimo = r.get("erro") or "accoreconsole falhou"
            else:
                ultimo = "accoreconsole indisponivel (%s)" % ultimo
        except Exception as e:
            ultimo = _com_erro(e)

        # 3) sem mais rotas: `SaveAs` renomearia o desenho da sessao do usuario.
        return CommandResult(
            ok=False,
            error="nao consegui exportar DXF (doc.Export e accoreconsole falharam: %s)" % ultimo,
        )

    async def drawing_purge(self) -> CommandResult:
        return self._aval('(progn (command "_.-PURGE" "_A" "*" "_N") T)')

    # -------------------------------------------------------------------- PDF
    # Folhas ISO em mm (retrato). Com PlotRotation=0 o AutoCAD imprime em
    # paisagem, entao a area util e (lado maior - margem) x (lado menor - margem).
    FOLHAS_MM = {"A4": (210.0, 297.0), "A3": (297.0, 420.0), "A2": (420.0, 594.0),
                 "A1": (594.0, 841.0), "A0": (841.0, 1189.0)}
    MARGEM_FOLHA_MM = 12.0

    async def _extensao_modelo(self):
        """(largura, altura) da extensao real do modelspace, ou None se vazio.

        Usa ZoomExtents + EXTMIN/EXTMAX e restaura a vista anterior. O caminho
        antigo (vla-GetBoundingBox por entidade dentro de vl-catch-all-apply)
        prendia o AutoCAD num prompt e travava o SendCommand por minutos.
        """
        expr = (
            '(progn'
            ' (setq __a (vlax-get-acad-object))'
            ' (vla-ZoomExtents __a)'
            ' (setq __r (list (car (getvar "EXTMIN")) (cadr (getvar "EXTMIN"))'
            '                 (car (getvar "EXTMAX")) (cadr (getvar "EXTMAX"))))'
            ' (vla-ZoomPrevious __a)'
            ' (if (> (caddr __r) (car __r)) __r nil))'
        )
        r = self._aval(expr, timeout=60.0)
        if not r.ok or not isinstance(r.payload, (list, tuple)) or len(r.payload) < 4:
            return None
        try:
            mnx, mny, mxx, mxy = (float(x) for x in r.payload[:4])
        except (TypeError, ValueError):
            return None
        if mxx <= mnx or mxy <= mny:
            return None
        return mxx - mnx, mxy - mny

    @classmethod
    def _util_folha(cls, nome: str):
        a, b = cls.FOLHAS_MM[nome]
        return max(a, b) - cls.MARGEM_FOLHA_MM, min(a, b) - cls.MARGEM_FOLHA_MM

    @classmethod
    def _folha_que_cabe(cls, need_w: float, need_h: float):
        for nome in ("A4", "A3", "A2", "A1", "A0"):
            uw, uh = cls._util_folha(nome)
            if max(need_w, need_h) <= uw and min(need_w, need_h) <= uh:
                return nome
        return None

    async def drawing_plot_pdf(self, path: str, media: str | None = None,
                               escala: float | None = None) -> CommandResult:
        """Plota o layout atual para PDF usando o plotter 'DWG To PDF.pc3'.

        `media` (ex. "A3") forca um tamanho de folha; sem ele a preferencia e A4.
        `escala` (ex. 50) aplica escala REAL 1:50. Sem `escala` o desenho e
        ajustado na folha (fit) -- nesse modo a escala do papel nao e controlada.
        Com `escala`, se `media` nao for informada a folha e escolhida sozinha
        (A4..A0) e, se nada couber, o plot falha explicando o porque.

        Se o PDF de destino estiver aberto/travado, o plot sai com nome
        temporario ao lado e o payload aponta o arquivo que realmente existe.
        """
        destino = Path(path)
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        try:
            doc = self._d()
        except Exception as e:
            return CommandResult(ok=False, error=_com_erro(e))

        # --- extensao real e unidades (antes de mexer no layout)
        ext = await self._extensao_modelo()
        try:
            insunits = int(self._chamar(doc.GetVariable, "INSUNITS") or 0)
        except Exception:
            insunits = 0
        mm_por_unidade = {1: 25.4, 2: 304.8, 4: 1.0, 5: 10.0, 6: 1000.0}.get(insunits, 1.0)

        folha = (media or "").strip().upper() or None
        detalhes = {"escala": ("1:%g" % escala) if escala else "ajustar"}
        if insunits not in (1, 2, 4, 5, 6):
            detalhes["aviso_unidades"] = (
                "INSUNITS=%s: assumi milimetro (1 unidade = 1 mm). Se o desenho esta "
                "em metros, rode system_run_command(\"_.INSUNITS 6\") e plote de novo." % insunits)
        if ext:
            detalhes["extensao"] = [round(ext[0], 3), round(ext[1], 3)]
        if escala:
            if escala <= 0:
                return CommandResult(ok=False, error="escala deve ser positiva (ex.: 50 para 1:50)")
            if not ext:
                return CommandResult(ok=False, error="modelspace vazio: nao ha o que plotar em escala")
            mm_papel_por_un = mm_por_unidade / float(escala)
            need_w, need_h = ext[0] * mm_papel_por_un, ext[1] * mm_papel_por_un
            detalhes["necessario_mm"] = [round(need_w, 1), round(need_h, 1)]
            if not folha:
                folha = self._folha_que_cabe(need_w, need_h)
                if not folha:
                    uw, uh = self._util_folha("A0")
                    return CommandResult(
                        ok=False,
                        error=("1:%g nao cabe em A0: precisa %.0fx%.0f mm e a area util de "
                               "A0 e %.0fx%.0f mm. Use uma escala maior (ex.: 1:%g)."
                               % (escala, need_w, need_h, uw, uh,
                                  max(1, int(escala * max(need_w / uw, need_h / uh) + 0.999)))))
                detalhes["folha_escolhida"] = folha
            elif folha in self.FOLHAS_MM:
                uw, uh = self._util_folha(folha)
                if max(need_w, need_h) > uw or min(need_w, need_h) > uh:
                    melhor = self._folha_que_cabe(need_w, need_h)
                    dica = ("use folha=%s" % melhor) if melhor else (
                        "use escala maior (ex.: 1:%g)"
                        % max(1, int(escala * max(need_w / uw, need_h / uh) + 0.999)))
                    return CommandResult(
                        ok=False,
                        error=("1:%g com extensao %.3gx%.3g unidades precisa %.0fx%.0f mm e "
                               "nao cabe em %s (util %.0fx%.0f mm). %s."
                               % (escala, ext[0], ext[1], need_w, need_h, folha, uw, uh, dica)))

        # Folha ISO e retrato (lado maior na vertical). Um desenho "deitado"
        # (largura > altura) precisa de PlotRotation=90 para nao ser cortado.
        rot = 0
        if ext and folha in self.FOLHAS_MM:
            a, b = self.FOLHAS_MM[folha]
            retrato = b > a
            if retrato == (ext[0] > ext[1]):
                rot = 1

        removido = True
        antigo_mtime = None
        if destino.exists():
            try:
                antigo_mtime = destino.stat().st_mtime
            except Exception:
                antigo_mtime = None
            try:
                destino.unlink()
            except Exception:
                removido = False
        alvo = destino
        if not removido:
            # Destino travado (PDF aberto no visualizador): grava ao lado.
            alvo = destino.with_name(destino.stem + "_tmp_plot.pdf")
            try:
                alvo.unlink()
            except Exception:
                pass
        posix = str(alvo).replace("\\", "/")
        try:
            try:
                self._chamar(doc.SetVariable, "BACKGROUNDPLOT", 0)
            except Exception:
                pass
            lay = self._chamar(lambda: doc.ActiveLayout)
            try:
                self._chamar(setattr, lay, "ConfigName", PLOTTER_PDF)
                self._chamar(lay.RefreshPlotDeviceInfo)
            except Exception:
                pass
            try:
                medias = list(self._chamar(lay.GetCanonicalMediaNames))
                pedida = folha or "A4"
                pref = [n for n in medias if pedida in n.upper()]
                if not pref:
                    pref = [n for n in medias if "A4" in n.upper()] or [n for n in medias if "A3" in n.upper()]
                    if folha:
                        detalhes["aviso_folha"] = (
                            "folha %s nao existe nesse plotter; usei %s"
                            % (folha, pref[0] if pref else "a atual"))
                if pref:
                    self._chamar(setattr, lay, "CanonicalMediaName", pref[0])
            except Exception:
                pass
            for attr, val in (
                ("PlotType", AC_EXTENTS),
                ("CenterPlot", True),
                ("PlotRotation", rot),
                ("StandardScale", AC_SCALE_TO_FIT),
                ("PlotWithPlotStyles", True),
                ("PlotHidden", False),
                ("PlotViewportBorders", False),
            ):
                try:
                    self._chamar(setattr, lay, attr, val)
                except Exception:
                    pass
            # Escala real por ULTIMO: qualquer setattr de layout depois disso
            # volta o StandardScale para "ajustar" e perde a escala.
            if escala:
                mm_papel_por_un = mm_por_unidade / float(escala)
                if mm_papel_por_un >= 1.0:
                    num, den = mm_papel_por_un, 1.0
                else:
                    num, den = 1.0, 1.0 / mm_papel_por_un
                try:
                    self._chamar(lay.SetCustomScale, num, den)
                except Exception as e:
                    return CommandResult(
                        ok=False,
                        error=_com_erro(e),
                        payload={"dica": "SetCustomScale falhou; use system_run_command "
                                          "(\"_.-PLOT ...\") ou plote sem escala"})
                detalhes["escala_com"] = "%.6g:%.6g" % (num, den)
                detalhes["mm_por_unidade_no_papel"] = round(mm_papel_por_un, 4)
            pl = self._chamar(lambda: doc.Plot)
            try:
                self._chamar(setattr, pl, "QuietErrorMode", True)
            except Exception:
                pass
            ok = self._chamar(pl.PlotToFile, posix, PLOTTER_PDF)
            t0 = time.time()
            while time.time() - t0 < 90:
                if alvo.exists() and alvo.stat().st_size > 500:
                    st = alvo.stat()
                    # So vale se o arquivo foi realmente regravado: unlink bem-sucedido
                    # ou mtime novo. Sem isso, um PDF travado no Acrobat fazia o plot
                    # devolver ok reaproveitando o arquivo velho (armadilha 16).
                    novo = removido or (antigo_mtime is not None and st.st_mtime > antigo_mtime + 0.001)
                    if novo:
                        payload = {"pdf": str(alvo), "bytes": st.st_size,
                                   "retorno": bool(ok), "folha": folha or "A4"}
                        payload.update(detalhes)
                        if alvo != destino:
                            # Tenta levar o PDF novo para o nome pedido; se o
                            # visualizador travar, devolve o temporario (existe).
                            try:
                                destino.write_bytes(alvo.read_bytes())
                                try:
                                    alvo.unlink()
                                except Exception:
                                    pass
                                payload["pdf"] = str(destino)
                                payload["bytes"] = destino.stat().st_size
                                payload["aviso"] = ("o PDF estava aberto; gravei em "
                                                    "'%s' e copiei por cima do destino" % alvo.name)
                            except Exception as e:
                                payload["aviso"] = ("o PDF '%s' esta aberto/travado (%s). "
                                                    "O desenho novo esta em '%s' -- feche o "
                                                    "visualizador e renomeie/repita."
                                                    % (destino.name, _com_erro(e), alvo.name))
                        return CommandResult(ok=True, payload=payload)
                time.sleep(0.25)
            return CommandResult(
                ok=False,
                error="PlotToFile executou mas o PDF nao foi regravado "
                      "(arquivo aberto/travado no visualizador?)",
                payload={"alvo": str(alvo)},
            )
        except Exception as e:
            return CommandResult(ok=False, error=_com_erro(e))

    # ------------------------------------------------------------- undo / view
    async def undo(self) -> CommandResult:
        return self._aval('(progn (command "_.U") T)')

    async def redo(self) -> CommandResult:
        return self._aval('(progn (command "_.REDO") T)')

    async def zoom_extents(self) -> CommandResult:
        return self._aval('(progn (command "_.ZOOM" "_E") T)')

    async def zoom_window(self, x1: float, y1: float, x2: float, y2: float) -> CommandResult:
        return self._aval(
            '(progn (command "_.ZOOM" "_W" (list %s %s 0.0) (list %s %s 0.0)) T)' % (x1, y1, x2, y2)
        )

    # ------------------------------------------------------------ LISP livre
    async def execute_lisp(self, code: str) -> CommandResult:
        return self._aval("(progn %s T)" % code)

    # -------------------------------------------------------------- entidades
    @staticmethod
    def _handle(expr_corpo: str) -> str:
        """Cria a entidade e devolve o HANDLE (estavel entre sessoes/saves)."""
        return '(progn (entmakex %s) (cdr (assoc 5 (entget (entlast)))))' % expr_corpo

    async def entmakex(self, corpo: str) -> CommandResult:
        """Cria uma entidade a partir de uma lista DXF ja montada. Devolve o HANDLE.

        Baixo nivel, usado pelo renderizador de plantas (`planta.py`): o corpo ja
        vem como expressao LISP, ex. `(list (cons 0 "LINE") ...)`.
        """
        return self._aval(self._handle(corpo))

    async def create_line(self, x1: float, y1: float, x2: float, y2: float, layer: str | None = None) -> CommandResult:
        lay = _q(layer or "0")
        corpo = (
            '(list (cons 0 "LINE") (cons 100 "AcDbEntity") (cons 8 "%s")'
            ' (cons 100 "AcDbLine") (cons 10 (list %s %s 0.0)) (cons 11 (list %s %s 0.0)))'
            % (lay, x1, y1, x2, y2)
        )
        return self._aval(self._handle(corpo))

    async def create_rectangle(self, x1: float, y1: float, x2: float, y2: float, layer: str | None = None) -> CommandResult:
        lay = _q(layer or "0")
        pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        cons10 = "".join(" (cons 10 (list %s %s))" % (p[0], p[1]) for p in pts)
        corpo = (
            '(list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 "%s")'
            ' (cons 100 "AcDbPolyline") (cons 90 4) (cons 70 1)%s)' % (lay, cons10)
        )
        return self._aval(self._handle(corpo))

    async def create_polyline(self, points, closed: bool = False, layer: str | None = None) -> CommandResult:
        lay = _q(layer or "0")
        cons10 = "".join(" (cons 10 (list %s %s))" % (p[0], p[1]) for p in points)
        corpo = (
            '(list (cons 0 "LWPOLYLINE") (cons 100 "AcDbEntity") (cons 8 "%s")'
            ' (cons 100 "AcDbPolyline") (cons 90 %d) (cons 70 %d)%s)'
            % (lay, len(points), 1 if closed else 0, cons10)
        )
        return self._aval(self._handle(corpo))

    async def create_circle(self, cx: float, cy: float, radius: float, layer: str | None = None) -> CommandResult:
        lay = _q(layer or "0")
        corpo = (
            '(list (cons 0 "CIRCLE") (cons 100 "AcDbEntity") (cons 8 "%s")'
            ' (cons 100 "AcDbCircle") (cons 10 (list %s %s 0.0)) (cons 40 %s))' % (lay, cx, cy, radius)
        )
        return self._aval(self._handle(corpo))

    async def create_arc(self, cx: float, cy: float, radius: float, start_angle: float, end_angle: float, layer: str | None = None) -> CommandResult:
        # entmake/entget do AutoLISP usam RADIANOS nos grupos 50/51 (ver tests/probe_arco4.py)
        lay = _q(layer or "0")
        corpo = (
            '(list (cons 0 "ARC") (cons 100 "AcDbEntity") (cons 8 "%s")'
            ' (cons 100 "AcDbCircle") (cons 10 (list %s %s 0.0)) (cons 40 %s)'
            ' (cons 100 "AcDbArc") (cons 50 (angtof "%s")) (cons 51 (angtof "%s")))'
            % (lay, cx, cy, radius, start_angle, end_angle)
        )
        return self._aval(self._handle(corpo))


    # --- lacunas do COM fechadas em 21/10/2026 (docs/AUDITORIA-AO-VIVO.md) ---

    async def create_ellipse(self, cx: float, cy: float, major_x: float, major_y: float,
                             ratio: float, layer: str | None = None) -> CommandResult:
        """Elipse (ELLIPSE do DXF): grupo 11 = eixo maior relativo ao centro.

        O COM nao tinha `create_ellipse` (so' o ezdxf tinha), mas a entidade e'
        simples de montar com `entmakex`: grupo 40 = razao menor/maior e
        41/42 = parametro inicial/final (radianos, 0..2pi = elipse inteira).
        """
        if not 0.0 < ratio <= 1.0:
            return CommandResult(ok=False, error="ratio deve estar em (0, 1]")
        lay = _q(layer or "0")
        corpo = (
            '(list (cons 0 "ELLIPSE") (cons 100 "AcDbEntity") (cons 8 "%s")'
            ' (cons 100 "AcDbEllipse") (cons 10 (list %s %s 0.0))'
            ' (cons 11 (list %s %s 0.0)) (cons 40 %s)'
            ' (cons 41 0.0) (cons 42 6.283185307179586))'
            % (lay, cx, cy, major_x, major_y, ratio)
        )
        return self._aval(self._handle(corpo))

    async def create_text(self, x: float, y: float, text: str, height: float = 2.5, rotation: float = 0.0, layer: str | None = None) -> CommandResult:
        lay = _q(layer or "0")
        corpo = (
            '(list (cons 0 "TEXT") (cons 100 "AcDbEntity") (cons 8 "%s")'
            ' (cons 100 "AcDbText") (cons 10 (list %s %s 0.0)) (cons 40 %s) (cons 1 "%s")'
            ' (cons 50 (angtof "%s")))'
            % (lay, x, y, height, _q(text), rotation)
        )
        return self._aval(self._handle(corpo))

    async def create_mtext(self, x: float, y: float, width: float, text: str, height: float = 2.5, layer: str | None = None) -> CommandResult:
        lay = _q(layer or "0")
        corpo = (
            '(list (cons 0 "MTEXT") (cons 100 "AcDbEntity") (cons 8 "%s")'
            ' (cons 100 "AcDbMText") (cons 10 (list %s %s 0.0)) (cons 40 %s) (cons 41 %s) (cons 1 "%s"))'
            % (lay, x, y, height, width, _q(text))
        )
        return self._aval(self._handle(corpo))

    async def create_hatch(self, entity_id: str, pattern: str = "ANSI31") -> CommandResult:
        """Hachura uma entidade fechada (por handle)."""
        expr = (
            '(progn (setq __e (handent "%s"))'
            ' (if __e (progn (command "_.-HATCH" "_P" "%s" "1" "0" "_S" __e "" "") T) nil))'
            % (_q(entity_id), _q(pattern))
        )
        return self._aval(expr)

    async def entity_list(self, layer: str | None = None, tipo: str | None = None) -> CommandResult:
        conds = []
        if layer:
            conds.append('(= (strcase (vla-get-Layer __e)) (strcase "%s"))' % _q(layer))
        if tipo:
            conds.append('(= (cdr (assoc 0 (entget (vlax-vla-object->ename __e)))) "%s")' % _q(tipo))
        if len(conds) > 1:
            cond = "(and " + " ".join(conds) + ")"
        elif conds:
            cond = conds[0]
        else:
            cond = "T"
        expr = (
            '(progn (vl-load-com) (setq __d (vla-get-ActiveDocument (vlax-get-acad-object)))'
            ' (setq __out "")'
            ' (vlax-for __e (vla-get-ModelSpace __d)'
            '  (if %s'
            '   (setq __out (strcat __out (vla-get-Handle __e) "|" (vla-get-ObjectName __e) "|"'
            '     (vla-get-Layer __e) "|"'
            '     (cdr (assoc 0 (entget (vlax-vla-object->ename __e)))) "\\n"))))'
            ' __out)' % cond
        )
        try:
            bruto = self._eval(expr)
        except Exception as e:
            return CommandResult(ok=False, error=str(e))
        itens = []
        if isinstance(bruto, str):
            for linha in bruto.split("\n"):
                p = linha.split("|")
                if len(p) >= 4 and p[0]:
                    itens.append({"handle": p[0], "tipo": p[3], "objeto": p[1], "camada": p[2]})
        # Mesmo shape do backend ezdxf ({"entities": [...], "count": N}). Antes
        # devolvia a lista crua, e qualquer consumidor escrito contra o ezdxf
        # estourava no motor COM -- medido em 21/10/2026.
        return CommandResult(ok=True, payload={"entities": itens, "count": len(itens)})

    async def entity_erase_filter(self, layer: str | None = None, tipo: str | None = None,
                                  texto: str | None = None, confirmar: bool = False) -> CommandResult:
        """Apaga em bloco por camada/tipo/conteudo. Sem nenhum filtro, recusa."""
        filtros = []
        if layer:
            filtros.append('(cons 8 "%s")' % _q(layer))
        if tipo:
            filtros.append('(cons 0 "%s")' % _q(tipo))
        if texto:
            filtros.append('(cons 1 "%s")' % _q(texto))
        if not filtros:
            return CommandResult(ok=False, error="informe ao menos um filtro (layer, tipo ou texto)")
        lst = "(list %s)" % " ".join(filtros)
        if confirmar:
            expr = ('(progn (setq __s (ssget "_X" %s))'
                    ' (if __s (progn (setq __n (sslength __s) __i 0)'
                    '   (repeat __n (entdel (ssname __s __i)) (setq __i (1+ __i))) __n) 0))' % lst)
        else:
            expr = '(progn (setq __s (ssget "_X" %s)) (if __s (sslength __s) 0))' % lst
        return self._aval(expr)

    async def entity_get(self, entity_id: str) -> CommandResult:
        expr = (
            '(progn (setq __e (handent "%s"))'
            ' (if __e (list (cons (quote handle) "%s")'
            '   (cons (quote tipo) (cdr (assoc 0 (entget __e))))'
            '   (cons (quote camada) (cdr (assoc 8 (entget __e))))'
            '   (cons (quote dxf) (vl-princ-to-string (entget __e)))) nil))'
            % (_q(entity_id), _q(entity_id))
        )
        return self._aval(expr)

    async def entity_erase(self, entity_id: str) -> CommandResult:
        return self._aval('(progn (setq __e (handent "%s")) (if __e (progn (entdel __e) 1) 0))'
                          % _q(entity_id))

    async def entity_move(self, entity_id: str, dx: float, dy: float) -> CommandResult:
        # vla-move em vez de (command "_.MOVE"): nao depende da linha de comando e
        # nao trava o AutoCAD quando ha comando ativo. handent devolve ENAME, por
        # isso o vlax-ename->vla-object: vla-move so aceita VLA-OBJECT.
        expr = (
            '(progn (vl-load-com) (setq __en (handent "%s"))'
            ' (if __en (progn (setq __e (vlax-ename->vla-object __en))'
            '  (vla-move __e (vlax-3d-point 0.0 0.0 0.0)'
            '  (vlax-3d-point %s %s 0.0)) 1) 0))' % (_q(entity_id), dx, dy)
        )
        return self._aval(expr)

    async def entity_copy(self, entity_id: str, dx: float, dy: float) -> CommandResult:
        expr = (
            '(progn (vl-load-com) (setq __en (handent "%s"))'
            ' (if __en (progn (setq __e (vlax-ename->vla-object __en))'
            '  (setq __n (vla-copy __e))'
            '  (vla-move __n (vlax-3d-point 0.0 0.0 0.0) (vlax-3d-point %s %s 0.0))'
            '  (vla-get-Handle __n)) 0))' % (_q(entity_id), dx, dy)
        )
        return self._aval(expr)

    async def entity_copy_filter(self, layer: str | None = None, tipo: str | None = None,
                                 dx: float = 0.0, dy: float = 0.0) -> CommandResult:
        """Copia em bloco tudo que casa com camada/tipo e desloca (dx, dy)."""
        conds = []
        if layer:
            conds.append('(= (strcase (vla-get-Layer __e)) (strcase "%s"))' % _q(layer))
        if tipo:
            conds.append('(= (cdr (assoc 0 (entget (vlax-vla-object->ename __e)))) "%s")' % _q(tipo))
        if not conds:
            return CommandResult(ok=False, error="informe ao menos um filtro (layer ou tipo)")
        cond = conds[0] if len(conds) == 1 else "(and " + " ".join(conds) + ")"
        expr = (
            '(progn (vl-load-com) (setq __d (vla-get-ActiveDocument (vlax-get-acad-object)))'
            ' (setq __hs (list))'
            ' (vlax-for __e (vla-get-ModelSpace __d)'
            '  (if %s (setq __hs (cons (vla-get-Handle __e) __hs))))'
            ' (setq __n 0)'
            ' (foreach __h __hs'
            '  (setq __o (handent __h))'
            '  (if __o (progn (setq __c (vla-copy (vlax-ename->vla-object __o)))'
            '   (vla-move __c (vlax-3d-point 0.0 0.0 0.0) (vlax-3d-point %s %s 0.0))'
            '   (setq __n (1+ __n)))))'
            ' __n)' % (cond, dx, dy)
        )
        return self._aval(expr)

    @staticmethod
    def _cond_filtro(layer: str | None, tipo: str | None):
        """Condicao LISP (dentro de vlax-for, variavel __e) para um filtro comum."""
        conds = []
        if layer:
            conds.append('(= (strcase (vla-get-Layer __e)) (strcase "%s"))' % _q(layer))
        if tipo:
            conds.append('(= (cdr (assoc 0 (entget (vlax-vla-object->ename __e)))) "%s")' % _q(tipo))
        if not conds:
            return None
        return conds[0] if len(conds) == 1 else "(and " + " ".join(conds) + ")"

    async def entity_mirror_filter(self, layer: str | None = None, tipo: str | None = None,
                                   x1: float | None = None, y1: float | None = None,
                                   x2: float | None = None, y2: float | None = None) -> CommandResult:
        """Espelha EM BLOCO (mantendo o original) tudo que casa com camada/tipo."""
        cond = self._cond_filtro(layer, tipo)
        if cond is None:
            return CommandResult(ok=False, error="informe ao menos um filtro (layer ou tipo)")
        if None in (x1, y1, x2, y2) or (abs(x1 - x2) < 1e-9 and abs(y1 - y2) < 1e-9):
            return CommandResult(
                ok=False,
                error="informe DOIS PONTOS DISTINTOS para o eixo de espelhamento "
                      "(x1,y1)-(x2,y2), ex.: x1=0,y1=0,x2=0,y2=1 para espelhar no eixo Y")
        expr = (
            '(progn (vl-load-com) (setq __d (vla-get-ActiveDocument (vlax-get-acad-object)))'
            ' (setq __hs (list))'
            ' (vlax-for __e (vla-get-ModelSpace __d)'
            '  (if %s (setq __hs (cons (vla-get-Handle __e) __hs))))'
            ' (setq __n 0)'
            ' (foreach __h __hs'
            '  (setq __o (handent __h))'
            '  (if __o (progn'
            '   (vla-mirror (vlax-ename->vla-object __o)'
            '    (vlax-3d-point %s %s 0.0) (vlax-3d-point %s %s 0.0))'
            '   (setq __n (1+ __n)))))'
            ' __n)' % (cond, x1, y1, x2, y2)
        )
        return self._aval(expr)

    async def entity_rotate_filter(self, layer: str | None = None, tipo: str | None = None,
                                   x: float = 0.0, y: float = 0.0,
                                   angulo: float = 0.0) -> CommandResult:
        """Gira EM BLOCO tudo que casa com camada/tipo em torno de (x, y)."""
        cond = self._cond_filtro(layer, tipo)
        if cond is None:
            return CommandResult(ok=False, error="informe ao menos um filtro (layer ou tipo)")
        expr = (
            '(progn (vl-load-com) (setq __d (vla-get-ActiveDocument (vlax-get-acad-object)))'
            ' (setq __hs (list))'
            ' (vlax-for __e (vla-get-ModelSpace __d)'
            '  (if %s (setq __hs (cons (vla-get-Handle __e) __hs))))'
            ' (setq __n 0)'
            ' (foreach __h __hs'
            '  (setq __o (handent __h))'
            '  (if __o (progn'
            '   (vla-rotate (vlax-ename->vla-object __o) (vlax-3d-point %s %s 0.0)'
            '    (* pi (/ %s 180.0)))'
            '   (setq __n (1+ __n)))))'
            ' __n)' % (cond, x, y, angulo)
        )
        return self._aval(expr)

    async def entity_rotate(self, entity_id: str, x: float, y: float, angulo: float) -> CommandResult:
        """Gira em torno do ponto (x, y). Angulo em GRAUS."""
        expr = (
            '(progn (vl-load-com) (setq __en (handent "%s"))'
            ' (if __en (progn (setq __e (vlax-ename->vla-object __en))'
            '  (vla-rotate __e (vlax-3d-point %s %s 0.0)'
            '  (* pi (/ %s 180.0))) 1) 0))' % (_q(entity_id), x, y, angulo)
        )
        return self._aval(expr)

    async def entity_mirror(self, entity_id: str, x1: float, y1: float,
                            x2: float, y2: float) -> CommandResult:
        """Espelha em relacao ao eixo (x1,y1)-(x2,y2), MANTENDO o original."""
        expr = (
            '(progn (vl-load-com) (setq __en (handent "%s"))'
            ' (if __en (progn (setq __e (vlax-ename->vla-object __en))'
            '  (setq __n (vla-mirror __e'
            '  (vlax-3d-point %s %s 0.0) (vlax-3d-point %s %s 0.0)))'
            '  (vla-get-Handle __n)) 0))' % (_q(entity_id), x1, y1, x2, y2)
        )
        return self._aval(expr)

    async def entity_offset(self, entity_id: str, distance: float, side: int = 1) -> CommandResult:
        """Cria uma paralela a LINE, a `distance` para o lado side (+1 esquerda da
        direcao, -1 direita). Devolve o handle novo. Outros tipos: erro explicito."""
        expr = (
            '(progn (vl-load-com) (setq __e (handent "%s"))'
            ' (if (not __e) 0'
            '  (if (/= (cdr (assoc 0 (entget __e))) "LINE") -1'
            '   (progn'
            '    (setq __p1 (cdr (assoc 10 (entget __e))) __p2 (cdr (assoc 11 (entget __e))))'
            '    (setq __dx (- (car __p2) (car __p1)) __dy (- (cadr __p2) (cadr __p1)))'
            '    (setq __L (sqrt (+ (* __dx __dx) (* __dy __dy))))'
            '    (if (< __L 1e-9) -2'
            '     (progn'
            '      (setq __nx (/ (* (- __dy) %s %d) __L)'
            '            __ny (/ (* __dx %s %d) __L))'
            '      (setq __h (entmakex (list (cons 0 "LINE")'
            '        (cons 8 (cdr (assoc 8 (entget __e))))'
            '        (cons 10 (list (+ (car __p1) __nx) (+ (cadr __p1) __ny) 0.0))'
            '        (cons 11 (list (+ (car __p2) __nx) (+ (cadr __p2) __ny) 0.0)))))'
            '      (if __h (cdr (assoc 5 (entget __h))) -3)))))))' % (_q(entity_id), distance, side, distance, side)
        )
        return self._aval(expr)


    # -------------------------------------------------------------- camadas
    async def layer_linetype_load(self, nome: str, arquivo: str = "acad.lin") -> CommandResult:
        """Carrega um tipo de linha e confirma que entrou na tabela LTYPE.

        Usa doc.Linetypes.Load (API COM) em vez de `-LINETYPE` na linha de comando:
        o comando fica esperando um ENTER extra depois do arquivo e travava o
        AutoCAD num prompt (todas as chamadas seguintes eram recusadas).
        """
        try:
            doc = self._d()
        except Exception as e:
            return CommandResult(ok=False, error=_com_erro(e))
        try:
            self._chamar(lambda: doc.Linetypes.Item(nome))
            return CommandResult(ok=True, payload={"linetype": nome, "ja_existia": True})
        except Exception:
            pass
        try:
            self._chamar(doc.Linetypes.Load, nome, arquivo)
        except Exception as e:
            return CommandResult(
                ok=False,
                error="nao carregou o LTYPE '%s' de '%s': %s (nomes comuns: DASHED, HIDDEN, "
                      "CENTER, PHANTOM; o arquivo precisa estar no Support Path)"
                      % (nome, arquivo, _com_erro(e)))
        try:
            self._chamar(lambda: doc.Linetypes.Item(nome))
        except Exception as e:
            return CommandResult(ok=False, error="LTYPE '%s' nao apareceu na tabela: %s"
                                                 % (nome, _com_erro(e)))
        return CommandResult(ok=True, payload={"linetype": nome, "ja_existia": False})

    async def layer_create(self, name: str, color: str | int = 7, linetype: str = "CONTINUOUS") -> CommandResult:
        try:
            cor = int(color)
        except Exception:
            mapa = {"red": 1, "yellow": 2, "green": 3, "cyan": 4, "blue": 5, "magenta": 6, "white": 7}
            cor = mapa.get(str(color).lower(), 7)
        # Tipo de linha que nao existe no desenho faz o entmakex FALHAR em silencio
        # (a camada nao e criada e o tool dizia ok). Aqui a falha e explicita e diz
        # exatamente o que rodar para carregar o LTYPE.
        expr = (
            '(progn'
            ' (if (and (not (tblsearch "LTYPE" "%s")) (not (equal (strcase "%s") "CONTINUOUS")))'
            '  (strcat "MCPERRO:tipo de linha %s nao existe no desenho.'
            ' Rode linetype_load(%s) (ou system_run_command(_.-LINETYPE _LOAD %s acad.lin)) e tente de novo.")'
            '  (progn'
            '   (if (not (tblsearch "LAYER" "%s"))'
            '    (entmakex (list (cons 0 "LAYER") (cons 100 "AcDbSymbolTableRecord")'
            '     (cons 100 "AcDbLayerTableRecord") (cons 2 "%s") (cons 70 0) (cons 62 %s) (cons 6 "%s"))))'
            '   (if (tblsearch "LAYER" "%s") 1'
            '    (strcat "MCPERRO:entmakex nao criou a camada %s")))))'
            % (linetype, linetype, linetype, linetype, linetype,
               _q(name), _q(name), cor, _q(linetype), _q(name), name)
        )
        return self._aval(expr)

    async def layer_set_current(self, name: str) -> CommandResult:
        return self._aval('(progn (setvar "CLAYER" "%s") T)' % _q(name))

    async def layer_set_properties(self, name: str, color=None, linetype=None, lineweight=None) -> CommandResult:
        pedacos = []
        if color is not None:
            try:
                cor = int(color)
            except Exception:
                mapa = {"red": 1, "yellow": 2, "green": 3, "cyan": 4, "blue": 5, "magenta": 6, "white": 7}
                cor = mapa.get(str(color).lower(), 7)
            pedacos.append('(command "_.-LAYER" "_C" "%s" "%s" "")' % (cor, _q(name)))
        if linetype:
            pedacos.append('(command "_.-LAYER" "_L" "%s" "%s" "")' % (_q(linetype), _q(name)))
        if lineweight:
            pedacos.append('(command "_.-LAYER" "_LW" "%s" "%s" "")' % (_q(lineweight), _q(name)))
        if not pedacos:
            return CommandResult(ok=True, payload={"no-op": name})
        return self._aval("(progn %s T)" % " ".join(pedacos))

    # ---------------------------------------------------------------- blocos
    async def block_insert(self, name: str, x: float, y: float, scale: float = 1.0, rotation: float = 0.0, block_id: str | None = None) -> CommandResult:
        """Insere um bloco. `ATTDIA`/`ATTREQ` em 0 para nao travar o AutoCAD.

        Um bloco com ATTDEF pede o valor de cada atributo; sem ATTDIA=0 o
        AutoCAD abre dialogo modal e sem ATTREQ=0 ele para no prompt de linha de
        comando — nos dois casos a sessao inteira trava (medido em 21/10/2026).
        """
        expr = (
            '(progn (setvar "ATTDIA" 0) (setvar "ATTREQ" 0)'
            ' (entmakex (list (cons 0 "INSERT") (cons 100 "AcDbEntity") (cons 8 "0")'
            ' (cons 100 "AcDbBlockReference") (cons 2 "%s") (cons 10 (list %s %s 0.0))'
            ' (cons 41 %s) (cons 42 %s) (cons 43 %s) (cons 50 (angtof "%s"))))'
            ' (cdr (assoc 5 (entget (entlast)))))' % (_q(name), x, y, scale, scale, scale, rotation)
        )
        return self._aval(expr)


    async def block_define(self, name: str, entities: list[dict]) -> CommandResult:
        """Define um bloco a partir de primitivas (LINE/CIRCLE/ATTDEF/TEXT).

        Usa Blocks.Add + AddLine/AddCircle/AddAttribute/AddText, que existem no
        COM — nao precisa do comando BLOCK (que abre dialogo).
        """
        partes = []
        for e in entities:
            tipo = e.get("type", "LINE")
            if tipo == "LINE":
                partes.append(
                    '(vla-AddLine __b (vlax-3d-point (list %s %s 0.0))'
                    ' (vlax-3d-point (list %s %s 0.0)))'
                    % (e.get("x1", 0), e.get("y1", 0), e.get("x2", 0), e.get("y2", 0)))
            elif tipo == "CIRCLE":
                partes.append(
                    '(vla-AddCircle __b (vlax-3d-point (list %s %s 0.0)) %s)'
                    % (e.get("cx", 0), e.get("cy", 0), e.get("radius", 1)))
            elif tipo == "ATTDEF":
                partes.append(
                    '(vla-AddAttribute __b %s 0 "%s" (vlax-3d-point (list %s %s 0.0))'
                    ' "%s" "%s")'
                    % (e.get("height", 2.5), _q(e.get("prompt", "")),
                       e.get("x", 0), e.get("y", 0), _q(e.get("tag", "TAG")),
                       _q(e.get("value", ""))))
            elif tipo == "TEXT":
                partes.append(
                    '(vla-AddText __b "%s" (vlax-3d-point (list %s %s 0.0)) %s)'
                    % (_q(e.get("text", "")), e.get("x", 0), e.get("y", 0),
                       e.get("height", 2.5)))
            else:
                return CommandResult(
                    ok=False,
                    error="tipo desconhecido: %r (use LINE/CIRCLE/ATTDEF/TEXT)" % tipo)
        corpo = (
            '(progn (vl-load-com) (setq __d (vla-get-ActiveDocument (vlax-get-acad-object)))'
            ' (if (tblsearch "BLOCK" "%s") "MCPERRO:bloco %s ja existe"'
            '  (progn (setq __b (vla-Add (vla-get-Blocks __d)'
            '   (vlax-3d-point (list 0.0 0.0 0.0)) "%s"))'
            '   %s'
            '   (vla-get-Name __b))))'
            % (_q(name), _q(name), _q(name), " ".join(partes) if partes else "T")
        )
        return self._aval(corpo)

    @staticmethod
    def _bloco_de(entity_id: str) -> str:
        """LISP que resolve o NOME do bloco dono da entidade (INSERT ou ATTDEF).

        Ler os atributos de um INSERT exige `vla-GetAttributes`, que devolve um
        safearray em variant cujo limite e' -1 quando o INSERT nao materializou
        atributos (medido em 21/10/2026) — e iterar esse array em LISP da
        "bad argument type: VLA-object collection". A definicao do bloco nao tem
        esse problema: os ATTDEF estao la como entidades comuns, lidos por
        `entget`. E' de la que sai o template (tag/prompt/valor/altura).
        """
        return (
            '(progn (vl-load-com) (setq __e (handent "%s"))'
            ' (if (null __e) "MCPERRO:handle nao existe"'
            '  (progn (setq __o (vlax-ename->vla-object __e))'
            '   (setq __tipo (vla-get-ObjectName __o))'
            '   (if (= __tipo "AcDbBlockReference")'
            '    (vla-get-Name __o)'
            '    (if (= __tipo "AcDbAttributeDefinition")'
            '     (progn (setq __achou "")'
            '      (vlax-for __b (vla-get-Blocks (vla-get-ActiveDocument (vlax-get-acad-object)))'
            '       (if (null __achou)'
            '        (vlax-for __x __b'
            '         (if (= (vlax-vla-object->ename __x) __e) (setq __achou (vla-get-Name __b))))))'
            '      (if (= __achou "") "MCPERRO:ATTDEF nao pertence a nenhum bloco" __achou))'
            '     "MCPERRO:entidade nao e INSERT nem ATTDEF")))))'
            % _q(entity_id)
        )

    async def block_get_attributes(self, entity_id: str) -> CommandResult:
        """Template de atributos do bloco (tag=valor, prompt, altura).

        Resolve o bloco dono da entidade e le os ATTDEF da definicao. Para um
        INSERT, o valor devolvido e' o default do ATTDEF; o valor efetivo de um
        INSERT so' existe quando ele foi inserido respondendo aos prompts.
        """
        expr = (
            '(progn (vl-load-com) (setq __nome %s)'
            ' (if (and (null __nome) (not (is-list __nome))) "MCPERRO:bloco nao resolvido"'
            '  (progn (setq __d (vla-get-ActiveDocument (vlax-get-acad-object)))'
            '   (if (null (tblsearch "BLOCK" __nome))'
            '    (strcat "MCPERRO:bloco " __nome " nao existe no desenho")'
            '    (progn (setq __out "")'
            '     (vlax-for __x (vla-item (vla-get-Blocks __d) __nome)'
            '      (if (= (cdr (assoc 0 (entget (vlax-vla-object->ename __x)))) "ATTDEF")'
            '       (progn (setq __e (entget (vlax-vla-object->ename __x)))'
            '        (setq __out (strcat __out (cdr (assoc 2 __e)) "=" (cdr (assoc 1 __e))'
            '         "|" (cdr (assoc 3 __e)) "|" (rtos (cdr (assoc 40 __e))) "\n")))))'
            '     (if (= __out "") "MCPERRO:bloco sem ATTDEF" __out))))))'
            % self._bloco_de(entity_id)
        )
        r = self._aval(expr)
        if r.ok and isinstance(r.payload, str) and not str(r.payload).startswith("MCPERRO:"):
            pares = {}
            for linha in str(r.payload).split("\n"):
                if "=" in linha:
                    tag, resto = linha.split("=", 1)
                    valor, prompt, altura = (resto.split("|") + ["", ""])[:3]
                    pares[tag] = {"valor": valor, "prompt": prompt, "altura": altura}
            r.payload = pares
        return r

    async def block_update_attribute(self, entity_id: str, tag: str, value: str) -> CommandResult:
        """Altera o valor default do ATTDEF `tag` na definicao do bloco."""
        expr = (
            '(progn (vl-load-com) (setq __nome %s)'
            ' (if (and (null __nome) (not (is-list __nome))) "MCPERRO:bloco nao resolvido"'
            '  (progn (setq __d (vla-get-ActiveDocument (vlax-get-acad-object)))'
            '   (if (null (tblsearch "BLOCK" __nome))'
            '    (strcat "MCPERRO:bloco " __nome " nao existe no desenho")'
            '    (progn (setq __ok nil)'
            '     (vlax-for __x (vla-item (vla-get-Blocks __d) __nome)'
            '      (if (= (cdr (assoc 0 (entget (vlax-vla-object->ename __x)))) "ATTDEF")'
            '       (progn (setq __e (entget (vlax-vla-object->ename __x)))'
            '        (if (= (strcase (cdr (assoc 2 __e))) (strcase "%s"))'
            '         (progn (entmod (subst (cons 1 "%s") (assoc 1 __e) __e)) (setq __ok T))))))'
            '     (if __ok T "MCPERRO:atributo %s nao existe no bloco"))))))'
            % (self._bloco_de(entity_id), _q(tag), _q(value), _q(tag))
        )
        return self._aval(expr)


    # ------------------------------------------------------------ cotas/texto
    async def create_dimension_linear(self, x1: float, y1: float, x2: float, y2: float, dim_x: float, dim_y: float) -> CommandResult:
        expr = (
            '(progn (setvar "CMDECHO" 0) (setvar "OSMODE" 0)'
            ' (command "_.DIMLINEAR" "_non" (list %s %s 0.0) "_non" (list %s %s 0.0) "_non" (list %s %s 0.0))'
            ' (if (entlast) (cdr (assoc 5 (entget (entlast)))) nil))'
            % (x1, y1, x2, y2, dim_x, dim_y)
        )
        return self._aval(expr)

    async def create_dimension_aligned(self, x1: float, y1: float, x2: float, y2: float, offset: float) -> CommandResult:
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        dx, dy = x2 - x1, y2 - y1
        n = max((dx * dx + dy * dy) ** 0.5, 1e-9)
        ox, oy = mx - dy / n * offset, my + dx / n * offset
        expr = (
            '(progn (setvar "CMDECHO" 0) (setvar "OSMODE" 0)'
            ' (command "_.DIMALIGNED" "_non" (list %s %s 0.0) "_non" (list %s %s 0.0) "_non" (list %s %s 0.0))'
            ' (if (entlast) (cdr (assoc 5 (entget (entlast)))) nil))' % (x1, y1, x2, y2, ox, oy)
        )
        return self._aval(expr)

    async def create_dimension_angular(self, cx: float, cy: float, x1: float, y1: float,
                                       x2: float, y2: float) -> CommandResult:
        """Cota angular do vertice (cx,cy) entre (x1,y1) e (x2,y2).

        Vai pela API (`IAcadBlock.AddDimAngular`), nao pelo comando DIMANGULAR:
        o comando com `_non` nos quatro pontos deixa o AutoCAD esperando selecao
        e trava a sessao (medido em 21/10/2026).
        """
        import math

        a1 = math.atan2(y1 - cy, x1 - cx)
        a2 = math.atan2(y2 - cy, x2 - cx)
        d = a2 - a1
        while d > math.pi:
            d -= 2.0 * math.pi
        while d < -math.pi:
            d += 2.0 * math.pi
        r = max(math.hypot(x1 - cx, y1 - cy), math.hypot(x2 - cx, y2 - cy), 1e-9)
        amid = a1 + d / 2.0
        lx, ly = cx + r * 1.5 * math.cos(amid), cy + r * 1.5 * math.sin(amid)
        expr = (
            '(progn (vl-load-com) (setq __d (vla-get-ActiveDocument (vlax-get-acad-object)))'
            ' (setq __m (vla-get-ModelSpace __d))'
            ' (vlax-invoke-method __m "AddDimAngular"'
            '  (vlax-3d-point (list %s %s 0.0)) (vlax-3d-point (list %s %s 0.0))'
            '  (vlax-3d-point (list %s %s 0.0)) (vlax-3d-point (list %s %s 0.0)))'
            ' (if (entlast) (cdr (assoc 5 (entget (entlast)))) nil))'
            % (cx, cy, x1, y1, x2, y2, lx, ly)
        )
        return self._aval(expr)

    async def create_dimension_radius(self, cx: float, cy: float, radius: float,
                                      angle: float = 0.0) -> CommandResult:
        """Cota de raio do circulo de centro (cx,cy) — `IAcadBlock.AddDimRadial`.

        Pela API nao precisa procurar a circunferencia: o centro e um ponto
        sobre ela (a `angle`) bastam, e `LeaderLength` = raio fica legivel.
        """
        import math

        a = math.radians(angle)
        px, py = cx + radius * math.cos(a), cy + radius * math.sin(a)
        expr = (
            '(progn (vl-load-com) (setq __d (vla-get-ActiveDocument (vlax-get-acad-object)))'
            ' (setq __m (vla-get-ModelSpace __d))'
            ' (vlax-invoke-method __m "AddDimRadial"'
            '  (vlax-3d-point (list %s %s 0.0)) (vlax-3d-point (list %s %s 0.0)) %s)'
            ' (if (entlast) (cdr (assoc 5 (entget (entlast)))) nil))'
            % (cx, cy, px, py, radius)
        )
        return self._aval(expr)
    # ----------------------------------------------------------- screenshot
    async def get_screenshot(self) -> CommandResult:
        try:
            from . import win32_bridge

            hwnd = win32_bridge.find_autocad_window()
            if not hwnd:
                return CommandResult(ok=False, error="janela do AutoCAD nao encontrada")
            from .screenshot_win import capturar

            png, largura, altura = capturar(hwnd, self._raiz)
            return CommandResult(ok=True, payload={"png": str(png), "largura": largura,
                                                   "altura": altura})
        except Exception as e:
            return CommandResult(ok=False, error=str(e))

    # --- primitivas novas (frente 2: contrato do autocad-mcp-pro) ---
    async def create_point(self, x: float, y: float, layer: str | None = None) -> CommandResult:
        lay = _q(layer or "0")
        corpo = ('(list (cons 0 "POINT") (cons 100 "AcDbEntity") (cons 8 "%s")'
                 ' (cons 100 "AcDbPoint") (cons 10 (list %s %s 0.0)))' % (lay, x, y))
        return self._aval(self._handle(corpo))

    async def create_spline(self, fit_points, layer: str | None = None) -> CommandResult:
        if len(fit_points) < 2:
            return CommandResult(ok=False, error="spline precisa de ao menos 2 pontos de ajuste")
        lay = _q(layer or "0")
        cons11 = "".join(" (cons 11 (list %s %s))" % (p[0], p[1]) for p in fit_points)
        corpo = ('(list (cons 0 "SPLINE") (cons 100 "AcDbEntity") (cons 8 "%s")'
                 ' (cons 100 "AcDbSpline") (cons 41 3.0)%s)' % (lay, cons11))
        return self._aval(self._handle(corpo))

    async def create_xline(self, x: float, y: float, angle_deg: float,
                           layer: str | None = None) -> CommandResult:
        import math as _m
        lay = _q(layer or "0")
        r = _m.radians(angle_deg)
        corpo = ('(list (cons 0 "XLINE") (cons 100 "AcDbEntity") (cons 8 "%s")'
                 ' (cons 100 "AcDbLine") (cons 10 (list %s %s 0.0))'
                 ' (cons 11 (list %s %s 0.0)))'
                 % (lay, x, y, x + _m.cos(r), y + _m.sin(r)))
        return self._aval(self._handle(corpo))

    async def entity_array_polar(self, entity_id: str, count: int, fill_angle: float,
                                 center_x: float, center_y: float) -> CommandResult:
        if count < 1:
            return CommandResult(ok=False, error="count deve ser >= 1")
        expr = (
            '(progn (setq __e (handent "%s"))'
            ' (if (null __e) "MCPERRO:handle nao existe"'
            '  (progn (setq __o (vlax-ename->vla-object __e)) (setq __i 1)'
            '   (while (< __i %d)'
            '    (vla-copy __o)'
            '    (vla-rotate (vlax-ename->vla-object (entlast))'
            '     (vlax-3d-point (list %s %s 0.0))'
            '     (/ (* pi %s __i) (* %d 180.0)))'
            '    (setq __i (1+ __i))) T)))'
            % (_q(entity_id), count, center_x, center_y, fill_angle, count)
        )
        r = self._aval(expr)
        if r.ok and not (isinstance(r.payload, str) and str(r.payload).startswith("MCPERRO:")):
            r.payload = {"criadas": count - 1, "total": count, "handle_base": entity_id}
        return r


    async def entity_scale(self, entity_id: str, cx: float, cy: float,
                           factor: float) -> CommandResult:
        """Escala uniforme em torno de (cx,cy) — IAcadEntity.ScaleEntity."""
        if factor == 0:
            return CommandResult(ok=False, error="factor 0 apagaria a entidade; use um valor != 0")
        expr = (
            '(progn (vl-load-com) (setq __e (handent "%s"))'
            ' (if (null __e) "MCPERRO:handle nao existe"'
            '  (progn (vla-ScaleEntity (vlax-ename->vla-object __e)'
            '   (vlax-3d-point (list %s %s 0.0)) %s)'
            '  (vla-get-Handle (vlax-ename->vla-object __e)))))'
            % (_q(entity_id), cx, cy, factor)
        )
        return self._aval(expr)

    async def entity_chamfer(self, entity_id1: str, entity_id2: str, dist1: float,
                             dist2: float) -> CommandResult:
        """Bisela o canto entre duas retas, por geometria propria (sem comando).

        O comando `CHAMFER` nao aceita as duas retas por argumento e a
        pre-selecao com `sssetfirst` nao e' consumida por ele — medido em
        21/10/2026, as duas retas ficam intactas. Entao o canto e' calculado:
        interseccao das retas, `dist1`/`dist2` ao longo de cada uma, as pontas
        sao reescritas com `entmod` e a reta do bisel e' criada.
        """
        if dist1 <= 0 or dist2 <= 0:
            return CommandResult(ok=False, error="dist1 e dist2 precisam ser > 0")
        expr = (
            '(progn (vl-load-com)'
            ' (setq __e1 (handent "%s")) (setq __e2 (handent "%s"))'
            ' (if (or (null __e1) (null __e2)) "MCPERRO:os dois handles precisam existir"'
            '  (progn (setq __d1 (entget __e1)) (setq __d2 (entget __e2))'
            '   (list (cdr (assoc 0 __d1)) (cdr (assoc 10 __d1)) (cdr (assoc 11 __d1))'
            '    (cdr (assoc 0 __d2)) (cdr (assoc 10 __d2)) (cdr (assoc 11 __d2))))))'
            % (_q(entity_id1), _q(entity_id2))
        )
        r = self._aval(expr)
        if not r.ok:
            return r
        dados = r.payload
        if not isinstance(dados, list) or len(dados) < 6:
            return CommandResult(ok=False, error="entity_chamfer precisa de duas entidades LINE")
        if dados[0] != "LINE" or dados[3] != "LINE":
            return CommandResult(ok=False, error="entity_chamfer so' opera entre duas LINE")
        p1, p2 = list(dados[1])[:2], list(dados[2])[:2]
        p3, p4 = list(dados[4])[:2], list(dados[5])[:2]

        def dist(a, b):
            return ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5

        # interseccao das duas retas (2D)
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-12:
            return CommandResult(ok=False, error="as retas sao paralelas: nao ha canto para biselar")
        ix = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / den
        iy = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / den
        canto = (ix, iy)

        def passo(de, limite, d):
            """Ponto a `d` de `de` na direcao de `limite`."""
            comp = dist(de, limite)
            if comp < 1e-12:
                return de
            t = min(d / comp, 1.0)
            return (de[0] + (limite[0] - de[0]) * t, de[1] + (limite[1] - de[1]) * t)

        # em cada reta, o extremo mais longe do canto e' o que leva a chanfro
        a_far = p2 if dist(canto, p2) >= dist(canto, p1) else p1
        b_far = p4 if dist(canto, p4) >= dist(canto, p3) else p3
        q1 = passo(canto, a_far, dist1)
        q2 = passo(canto, b_far, dist2)

        corpo = (
            '(progn (vl-load-com)'
            ' (setq __d1 (subst (cons 11 (list %s %s 0.0)) (assoc 11 __d1) __d1))'
            ' (entmod __d1)'
            ' (setq __d2 (subst (cons 10 (list %s %s 0.0)) (assoc 10 __d2) __d2))'
            ' (entmod __d2)'
            ' (entmakex (list (cons 0 "LINE") (cons 100 "AcDbEntity") (cons 8 "0")'
            '  (cons 100 "AcDbLine") (cons 10 (list %s %s 0.0)) (cons 11 (list %s %s 0.0))))'
            ' (cdr (assoc 5 (entget (entlast)))))'
            % (q1[0], q1[1], q2[0], q2[1], q1[0], q1[1], q2[0], q2[1])
        )
        r = self._aval(corpo)
        if r.ok:
            r.payload = {"handle_bisel": r.payload, "canto": [ix, iy],
                         "dist1": dist1, "dist2": dist2}
        return r
    async def entity_array(self, entity_id: str, rows: int, cols: int,
                           row_dist: float, col_dist: float) -> CommandResult:
        """Repete uma entidade numa grade rows x cols (IAcadEntity.ArrayRectangular).

        ARRAYRECT e' interativo (pede linhas/colunas por dynamic input); a API
        faz a grade de uma vez. O numero de copias e' medido pela contagem de
        entidades do ModelSpace antes/depois — o retorno do metodo e' um vetor
        variant, que nao tem tamanho estavel em LISP.
        """
        expr = (
            '(progn (vl-load-com) (setq __d (vla-get-ActiveDocument (vlax-get-acad-object)))'
            ' (setq __n0 (vla-get-Count (vla-get-ModelSpace __d)))'
            ' (setq __e (handent "%s"))'
            ' (if (null __e) "MCPERRO:handle nao existe"'
            '  (progn (vlax-invoke-method (vlax-ename->vla-object __e) "ArrayRectangular"'
            '   %d %d 1 %s %s 0.0)'
            '   (- (vla-get-Count (vla-get-ModelSpace __d)) __n0))))'
            % (_q(entity_id), rows, cols, row_dist, col_dist)
        )
        r = self._aval(expr)
        if r.ok and isinstance(r.payload, int) and not str(r.payload).startswith("MCPERRO:"):
            r.payload = {"criadas": r.payload, "rows": rows, "cols": cols, "handle_base": entity_id}
        return r
    async def entity_set_properties(self, entity_id: str, layer: str | None = None,
                                    color: int | str | None = None,
                                    linetype: str | None = None,
                                    lineweight: int | None = None,
                                    visible: bool | None = None) -> CommandResult:
        def trecho(grupo, valor):
            return '(if %s (setq __d (subst (cons %s %s) (assoc %s __d) __d)))' % (
                _q(valor), grupo, valor, grupo)

        partes = []
        if layer is not None:
            partes.append(trecho(8, _q(layer)))
        if color is not None:
            partes.append(trecho(62, color))
        if linetype is not None:
            partes.append(trecho(6, _q(linetype)))
        if lineweight is not None:
            partes.append(trecho(370, lineweight))
        if visible is not None:
            partes.append(trecho(60, 1 if not visible else 0))
        if not partes:
            return CommandResult(ok=False, error="nenhuma propriedade informada")
        expr = ('(progn (setq __e (handent "%s")) (if (null __e) "MCPERRO:handle nao existe"'
                ' (progn (setq __d (entget __e)) %s (entmod __d) (entupd __e) T)))'
                % (_q(entity_id), " ".join(partes)))
        return self._aval(expr)

    async def entity_edit_text(self, entity_id: str, text: str | None = None,
                               height: float | None = None,
                               rotation: float | None = None) -> CommandResult:
        partes = []
        if text is not None:
            partes.append('(setq __d (subst (cons 1 %s) (assoc 1 __d) __d))' % _q(text))
        if height is not None:
            partes.append('(setq __d (subst (cons 40 %s) (assoc 40 __d) __d))' % height)
        if rotation is not None:
            partes.append('(setq __d (subst (cons 50 %s) (assoc 50 __d) __d))' % rotation)
        if not partes:
            return CommandResult(ok=False, error="nada para alterar (text/height/rotation)")
        expr = ('(progn (setq __e (handent "%s")) (if (null __e) "MCPERRO:handle nao existe"'
                ' (progn (setq __d (entget __e)) %s (entmod __d) (entupd __e) T)))'
                % (_q(entity_id), " ".join(partes)))
        return self._aval(expr)

    async def entity_delete_many(self, handles: list) -> CommandResult:
        if not handles:
            return CommandResult(ok=False, error="lista de handles vazia")
        lis = " ".join('(entdel (handent "%s"))' % _q(str(h)) for h in handles)
        r = self._aval("(progn %s T)" % lis)
        if r.ok:
            r.payload = {"apagadas": len(handles), "pedidas": len(handles), "falhas": []}
        return r

    async def hatch_edit(self, entity_id: str, pattern: str | None = None,
                         scale: float | None = None, angle: float | None = None,
                         color: int | str | None = None,
                         style: str | None = None) -> CommandResult:
        # No DXF o HATCH nao guarda escala/angulo por entidade (ficam na tabela
        # de padroes), entao o motor COM so' escreve o que o formato suporta.
        partes, mudou = [], []
        if pattern is not None:
            partes.append('(setq __d (subst (cons 2 %s) (assoc 2 __d) __d))' % _q(pattern))
            mudou.append("pattern")
        if color is not None:
            partes.append('(setq __d (subst (cons 62 %s) (assoc 62 __d) __d))' % color)
            mudou.append("color")
        if not partes:
            return CommandResult(ok=False, error="motor COM so suporta pattern/color no HATCH")
        if scale is not None or angle is not None or style is not None:
            mudou.append("(scale/angle/style: nao persistem por HATCH no DXF)")
        expr = ('(progn (setq __e (handent "%s")) (if (null __e) "MCPERRO:handle nao existe"'
                ' (progn (setq __d (entget __e)) %s (entmod __d) (entupd __e) T)))'
                % (_q(entity_id), " ".join(partes)))
        return self._aval(expr)

    async def drawing_properties_get(self) -> CommandResult:
        """SummaryInfo de verdade (o que o DWGPROPS do AutoCAD mostra)."""
        try:
            si = self._chamar(lambda: self._d().SummaryInfo)
            return CommandResult(ok=True, payload={
                "title": str(self._chamar(lambda: si.Title)),
                "subject": str(self._chamar(lambda: si.Subject)),
                "author": str(self._chamar(lambda: si.Author)),
                "keywords": str(self._chamar(lambda: si.Keywords)),
                "comments": str(self._chamar(lambda: si.Comments)),
                "where": "SummaryInfo do documento",
            })
        except Exception as exc:
            return CommandResult(ok=False, error=_com_erro(exc))

    async def drawing_properties_set(self, title: str | None = None, subject: str | None = None,
                                     author: str | None = None, keywords: str | None = None,
                                     comments: str | None = None,
                                     custom: dict | None = None) -> CommandResult:
        """Grava o SummaryInfo do documento (DWGPROPS)."""
        gravou = []
        try:
            si = self._chamar(lambda: self._d().SummaryInfo)
            for campo, valor in (("Title", title), ("Subject", subject), ("Author", author),
                                 ("Keywords", keywords), ("Comments", comments)):
                if valor is not None:
                    self._chamar(lambda c=campo, v=valor: setattr(si, c, v))
                    gravou.append(campo.lower())
            if custom:
                for nome, valor in custom.items():
                    try:
                        self._chamar(lambda n=nome, v=valor: si.SetCustomBySummaryInfo(n, v))
                        gravou.append("custom:%s" % nome)
                    except Exception as exc:      # noqa: BLE001
                        return CommandResult(ok=False, error="custom '%s': %s" % (nome, _com_erro(exc)))
            return CommandResult(ok=True, payload={"gravou": gravou,
                                                   "onde": "SummaryInfo do documento"})
        except Exception as exc:
            return CommandResult(ok=False, error=_com_erro(exc))

    async def entity_geometry(self, entity_id: str) -> CommandResult:
        """Geometria normalizada (pontos, centro, raio, angulos) de uma entidade.

        O LISP le os grupos DXF 10/11/40/50/51. Para LWPOLYLINE o grupo 10 se
        repete: o codigo coleta todos.
        """
        expr = (
            '(progn (setq __e (handent "%s"))'
            ' (if (null __e) "MCPERRO:handle nao existe"'
            '  (progn (setq __d (entget __e)) (setq __ps nil)'
            '   (foreach __c __d (if (= (car __c) 10)'
            '    (setq __ps (cons (list (car (cdr __c)) (cadr (cdr __c))) __ps))))'
            '   (list (cons (quote tipo) (cdr (assoc 0 __d)))'
            '    (cons (quote camada) (cdr (assoc 8 __d)))'
            '    (cons (quote pontos) (reverse __ps))'
            '    (cons (quote centro) (cdr (assoc 10 __d)))'
            '    (cons (quote raio) (cdr (assoc 40 __d)))'
            '    (cons (quote razao) (cdr (assoc 42 __d)))'
            '    (cons (quote angulo_inicio) (cdr (assoc 50 __d)))'
            '    (cons (quote angulo_fim) (cdr (assoc 51 __d)))'
            '    (cons (quote tipo) (cdr (assoc 0 __d)))))))'
            % _q(entity_id)
        )
        r = self._aval(expr)
        # O LISP devolve uma lista de pares ((tipo . "LINE") (camada . "PAREDES"));
        # o backend ezdxf devolve dict. Normaliza para o MESMO shape -- senao
        # entity_get / point_from_snap / point_tangent / hatch_material /
        # selection_window estouram no motor COM (medido em 21/10/2026).
        if r.ok and isinstance(r.payload, list):
            itens: dict = {}
            for par in r.payload:
                if isinstance(par, (list, tuple)) and len(par) >= 2:
                    itens[str(par[0])] = par[1]
            r.payload = itens
        return r

    # --- Operacoes geometricas (trim/extend/fillet) via ponte .NET ---

    async def entity_trim(self, alvo: str, corte: str, keep: list[float]) -> CommandResult:
        """Encurta a reta `alvo` ate a `corte`.

        Usa a ponte .NET (plugin CadMcpBridge) que executa dentro do AutoCAD
        com geometria nativa, sem passar por SendCommand.
        """
        try:
            from .bridge import Ponte, PonteIndisponivel
            p = Ponte(timeout=15)
            return CommandResult(ok=True, payload=p.trim(alvo=alvo, corte=corte, keep=keep))
        except (PonteIndisponivel, Exception) as e:
            return CommandResult(ok=False, error="ponte .NET nao disponivel: %s" % e)

    async def entity_extend(self, alvo: str, limite: str,
                            ponto: list[float] | None = None) -> CommandResult:
        """Estende a reta `alvo` ate a `limite`."""
        try:
            from .bridge import Ponte, PonteIndisponivel
            p = Ponte(timeout=15)
            return CommandResult(ok=True, payload=p.extend(alvo=alvo, limite=limite, ponto=ponto))
        except (PonteIndisponivel, Exception) as e:
            return CommandResult(ok=False, error="ponte .NET nao disponivel: %s" % e)

    async def entity_fillet(self, h1: str, h2: str, raio: float,
                            trim: bool = True, p1: list[float] | None = None,
                            p2: list[float] | None = None) -> CommandResult:
        """Arredonda o canto entre duas retas com arco de `raio`."""
        try:
            from .bridge import Ponte, PonteIndisponivel
            p = Ponte(timeout=15)
            return CommandResult(ok=True, payload=p.fillet(h1=h1, h2=h2, raio=raio, trim=trim, p1=p1, p2=p2))
        except (PonteIndisponivel, Exception) as e:
            return CommandResult(ok=False, error="ponte .NET nao disponivel: %s" % e)

    async def plot_style_list(self) -> CommandResult:
        """Lista os estilos de plotagem (.ctb/.stb) do AutoCAD."""
        estilos: set[str] = set()
        try:
            app = self._app
            plot_factory = app.PlotConfigurations
            for pc in plot_factory:
                try:
                    estilo = pc.PlotStyleSheet
                    if estilo and estilo.lower().endswith((".ctb", ".stb")):
                        estilos.add(estilo)
                except Exception:
                    pass
            return CommandResult(ok=True, payload=sorted(estilos))
        except Exception:
            return CommandResult(ok=False, error="nao foi possivel listar estilos de plotagem")
