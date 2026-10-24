"""File-based IPC backend for AutoCAD LT.

Protocol:
1. Python writes JSON command to C:/temp/autocad_mcp_cmd_{request_id}.json
2. Python types the fixed string "(c:mcp-dispatch)" + Enter
3. LISP reads cmd, dispatches via command map, writes result to
   C:/temp/autocad_mcp_result_{request_id}.json
4. Python polls for result file (100ms intervals, 10s timeout)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path

import structlog

from autocad_mcp.backends.base import AutoCADBackend, BackendCapabilities, CommandResult
from autocad_mcp.config import IPC_DIR, IPC_TIMEOUT, LISP_DIR

log = structlog.get_logger()

# IPC settings
POLL_INTERVAL = 0.1  # seconds
TIMEOUT = IPC_TIMEOUT  # seconds (configurable via AUTOCAD_MCP_IPC_TIMEOUT)
STALE_THRESHOLD = 60.0  # clean up files older than this


def find_autocad_window() -> int | None:
    """Find the AutoCAD LT window handle by checking window titles."""
    if sys.platform != "win32":
        return None
    try:
        import win32gui

        windows: list[int] = []

        def callback(hwnd, result):
            if win32gui.IsWindowVisible(hwnd):
                text = win32gui.GetWindowText(hwnd).lower()
                if "autocad" in text and ("drawing" in text or ".dwg" in text):
                    result.append(hwnd)
            return True

        win32gui.EnumWindows(callback, windows)
        return windows[0] if windows else None
    except ImportError:
        return None


class FileIPCBackend(AutoCADBackend):
    """File-based IPC with AutoCAD LT via mcp_dispatch.lsp."""

    def __init__(self):
        self._hwnd: int | None = None
        self._command_hwnd: int | None = None
        self._ipc_dir = Path(IPC_DIR)
        self._screenshot_provider = None
        self._lock = asyncio.Lock()  # Single in-flight command

    @property
    def name(self) -> str:
        return "file_ipc"

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

    async def initialize(self) -> CommandResult:
        """Find AutoCAD window and verify dispatcher is loaded."""
        self._hwnd = find_autocad_window()
        if not self._hwnd:
            return CommandResult(ok=False, error="AutoCAD LT window not found")

        # Set up screenshot provider
        try:
            from autocad_mcp.screenshot import Win32ScreenshotProvider

            self._screenshot_provider = Win32ScreenshotProvider(self._hwnd)
        except Exception:
            pass

        # Find command-line child edit control for focus-free dispatch
        self._command_hwnd = self._find_command_line_hwnd()
        log.info("command_line_hwnd", hwnd=self._command_hwnd)

        # Ensure IPC directory exists
        self._ipc_dir.mkdir(parents=True, exist_ok=True)

        # Clean up stale IPC files
        self._cleanup_stale_files()

        # Ping the dispatcher to verify it's loaded
        result = await self._dispatch("ping", {})
        if not result.ok:
            lisp_path = str(LISP_DIR / "mcp_dispatch.lsp").replace("\\", "/")
            return CommandResult(
                ok=False,
                error=(
                    "AutoCAD LT detected but mcp_dispatch.lsp not loaded.\n"
                    f'In AutoCAD command line, type:\n  (load "{lisp_path}")\n'
                    "Or add lisp-code/ to trusted paths for auto-loading."
                ),
            )

        return CommandResult(ok=True, payload={"backend": "file_ipc", "hwnd": self._hwnd})

    async def status(self) -> CommandResult:
        info = {
            "backend": "file_ipc",
            "hwnd": self._hwnd,
            "ipc_dir": str(self._ipc_dir),
            "capabilities": {k: v for k, v in self.capabilities.__dict__.items()},
        }
        return CommandResult(ok=True, payload=info)

    # --- IPC dispatch ---

    async def _dispatch(self, command: str, params: dict) -> CommandResult:
        """Send a command via file IPC and wait for result."""
        async with self._lock:
            return await self._dispatch_unlocked(command, params)

    async def _dispatch_unlocked(self, command: str, params: dict) -> CommandResult:
        """Core IPC logic (must be called under _lock)."""
        request_id = uuid.uuid4().hex[:12]
        cmd_file = self._ipc_dir / f"autocad_mcp_cmd_{request_id}.json"
        result_file = self._ipc_dir / f"autocad_mcp_result_{request_id}.json"
        tmp_file = cmd_file.with_suffix(".tmp")

        try:
            # Strip None values — the simple LISP JSON parser can't handle null
            clean_params = {k: v for k, v in params.items() if v is not None}
            # Atomic write: write to .tmp, then rename
            payload = {
                "request_id": request_id,
                "command": command,
                "params": clean_params,
                "ts": time.time(),
            }
            tmp_file.write_text(json.dumps(payload), encoding="utf-8")
            tmp_file.rename(cmd_file)

            # Type the fixed dispatch trigger
            self._type_dispatch_trigger()

            # Poll for result
            deadline = time.time() + TIMEOUT
            while time.time() < deadline:
                if result_file.exists():
                    try:
                        # AutoCAD LISP writes files in Windows-1252 encoding;
                        # try UTF-8 first (covers ASCII), fall back to cp1252
                        try:
                            text = result_file.read_text(encoding="utf-8")
                        except UnicodeDecodeError:
                            text = result_file.read_text(encoding="cp1252")
                        data = json.loads(text)
                        # Verify request_id matches
                        if data.get("request_id") == request_id:
                            return CommandResult(
                                ok=data.get("ok", False),
                                payload=data.get("payload"),
                                error=data.get("error"),
                            )
                    except (json.JSONDecodeError, OSError):
                        pass  # File may be partially written, retry
                await asyncio.sleep(POLL_INTERVAL)

            return CommandResult(ok=False, error=f"Timeout waiting for result (request_id={request_id})")

        finally:
            # Cleanup
            for f in (cmd_file, result_file, tmp_file):
                try:
                    f.unlink(missing_ok=True)
                except OSError:
                    pass

    def _find_command_line_hwnd(self) -> int | None:
        """Find AutoCAD's MDIClient child window for command routing."""
        if sys.platform != "win32" or not self._hwnd:
            return None
        try:
            import win32gui

            mdi_client: list[int] = []

            def cb(child_hwnd, _):
                if win32gui.GetClassName(child_hwnd) == "MDIClient":
                    mdi_client.append(child_hwnd)
                    return False  # stop enumeration
                return True

            win32gui.EnumChildWindows(self._hwnd, cb, None)
            return mdi_client[0] if mdi_client else None
        except Exception:
            return None

    def _type_dispatch_trigger(self):
        """Post '(c:mcp-dispatch)' + Enter via WM_CHAR to MDIClient — no focus steal.

        Sends ESC keystrokes first to cancel any stale pending command
        (e.g. from a previous timeout leaving AutoCAD in a command prompt).
        """
        try:
            import ctypes

            WM_CHAR = 0x0102
            WM_KEYDOWN = 0x0100
            WM_KEYUP = 0x0101
            VK_ESCAPE = 0x1B
            target = self._command_hwnd or self._hwnd
            post = ctypes.windll.user32.PostMessageW

            # Cancel any pending command (2x ESC for nested commands)
            for _ in range(2):
                post(target, WM_KEYDOWN, VK_ESCAPE, 0)
                post(target, WM_KEYUP, VK_ESCAPE, 0)
            time.sleep(0.05)

            for ch in "(c:mcp-dispatch)":
                post(target, WM_CHAR, ord(ch), 0)
            # Enter = carriage return
            post(target, WM_CHAR, 0x0D, 0)
            time.sleep(0.05)
        except Exception as e:
            log.error("dispatch_trigger_failed", error=str(e))

    def _cleanup_stale_files(self):
        """Remove stale IPC files from previous sessions."""
        try:
            now = time.time()
            for pattern in ("autocad_mcp_*.json", "autocad_mcp_*.tmp", "autocad_mcp_lisp_*.lsp"):
                for f in self._ipc_dir.glob(pattern):
                    if now - f.stat().st_mtime > STALE_THRESHOLD:
                        f.unlink(missing_ok=True)
        except OSError:
            pass

    # --- Drawing management ---

    async def drawing_info(self) -> CommandResult:
        return await self._dispatch("drawing-info", {})

    async def drawing_save(self, path: str | None = None) -> CommandResult:
        return await self._dispatch("drawing-save", {"path": path})

    async def drawing_save_as_dxf(self, path: str) -> CommandResult:
        return await self._dispatch("drawing-save-as-dxf", {"path": path})

    async def drawing_create(self, name: str | None = None) -> CommandResult:
        return await self._dispatch("drawing-create", {"name": name})

    async def drawing_purge(self) -> CommandResult:
        return await self._dispatch("drawing-purge", {})

    async def drawing_plot_pdf(self, path: str) -> CommandResult:
        return await self._dispatch("drawing-plot-pdf", {"path": path})

    async def drawing_get_variables(self, names: list[str] | None = None) -> CommandResult:
        if names:
            # Strip $ prefix for AutoCAD compatibility (ezdxf uses $ACADVER, AutoCAD uses ACADVER)
            clean_names = [n.lstrip("$") for n in names]
            names_str = ";".join(clean_names)
        else:
            names_str = ""
        return await self._dispatch("drawing-get-variables", {"names_str": names_str})

    async def drawing_open(self, path: str) -> CommandResult:
        return await self._dispatch("drawing-open", {"path": path})

    # --- Undo / Redo ---

    async def undo(self) -> CommandResult:
        return await self._dispatch("undo", {})

    async def redo(self) -> CommandResult:
        return await self._dispatch("redo", {})

    # --- Freehand LISP execution ---

    async def execute_lisp(self, code: str) -> CommandResult:
        """Execute arbitrary AutoLISP code via temp file.

        File persists for session; cleaned up by _cleanup_stale_files().
        """
        request_id = uuid.uuid4().hex[:12]
        code_file = self._ipc_dir / f"autocad_mcp_lisp_{request_id}.lsp"
        code_file.write_text(code, encoding="utf-8")
        return await self._dispatch("execute-lisp", {
            "code_file": str(code_file).replace("\\", "/")
        })

    # --- Entity operations ---

    async def create_line(self, x1, y1, x2, y2, layer=None) -> CommandResult:
        return await self._dispatch("create-line", {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "layer": layer})

    async def create_circle(self, cx, cy, radius, layer=None) -> CommandResult:
        return await self._dispatch("create-circle", {"cx": cx, "cy": cy, "radius": radius, "layer": layer})

    async def create_polyline(self, points, closed=False, layer=None) -> CommandResult:
        pts_str = ";".join(f"{p[0]},{p[1]}" for p in points)
        return await self._dispatch("create-polyline", {
            "points_str": pts_str, "closed": "1" if closed else "0", "layer": layer
        })

    async def create_rectangle(self, x1, y1, x2, y2, layer=None) -> CommandResult:
        return await self._dispatch("create-rectangle", {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "layer": layer})

    async def create_arc(self, cx, cy, radius, start_angle, end_angle, layer=None) -> CommandResult:
        return await self._dispatch("create-arc", {"cx": cx, "cy": cy, "radius": radius, "start_angle": start_angle, "end_angle": end_angle, "layer": layer})

    async def create_ellipse(self, cx, cy, major_x, major_y, ratio, layer=None) -> CommandResult:
        return await self._dispatch("create-ellipse", {"cx": cx, "cy": cy, "major_x": major_x, "major_y": major_y, "ratio": ratio, "layer": layer})

    async def create_mtext(self, x, y, width, text, height=2.5, layer=None) -> CommandResult:
        return await self._dispatch("create-mtext", {"x": x, "y": y, "width": width, "text": text, "height": height, "layer": layer})

    async def create_hatch(self, entity_id, pattern="ANSI31") -> CommandResult:
        return await self._dispatch("create-hatch", {"entity_id": entity_id, "pattern": pattern})

    async def entity_list(self, layer=None) -> CommandResult:
        return await self._dispatch("entity-list", {"layer": layer})

    async def entity_count(self, layer=None) -> CommandResult:
        return await self._dispatch("entity-count", {"layer": layer})

    async def entity_get(self, entity_id) -> CommandResult:
        return await self._dispatch("entity-get", {"entity_id": entity_id})

    async def entity_erase(self, entity_id) -> CommandResult:
        return await self._dispatch("entity-erase", {"entity_id": entity_id})

    async def entity_copy(self, entity_id, dx, dy) -> CommandResult:
        return await self._dispatch("entity-copy", {"entity_id": entity_id, "dx": dx, "dy": dy})

    async def entity_move(self, entity_id, dx, dy) -> CommandResult:
        return await self._dispatch("entity-move", {"entity_id": entity_id, "dx": dx, "dy": dy})

    async def entity_rotate(self, entity_id, cx, cy, angle) -> CommandResult:
        return await self._dispatch("entity-rotate", {"entity_id": entity_id, "cx": cx, "cy": cy, "angle": angle})

    async def entity_scale(self, entity_id, cx, cy, factor) -> CommandResult:
        return await self._dispatch("entity-scale", {"entity_id": entity_id, "cx": cx, "cy": cy, "factor": factor})

    async def entity_mirror(self, entity_id, x1, y1, x2, y2) -> CommandResult:
        return await self._dispatch("entity-mirror", {"entity_id": entity_id, "x1": x1, "y1": y1, "x2": x2, "y2": y2})

    async def entity_offset(self, entity_id, distance) -> CommandResult:
        return await self._dispatch("entity-offset", {"entity_id": entity_id, "distance": distance})

    async def entity_array(self, entity_id, rows, cols, row_dist, col_dist) -> CommandResult:
        return await self._dispatch("entity-array", {"entity_id": entity_id, "rows": rows, "cols": cols, "row_dist": row_dist, "col_dist": col_dist})

    async def entity_fillet(self, entity_id1, entity_id2, radius) -> CommandResult:
        return await self._dispatch("entity-fillet", {"id1": entity_id1, "id2": entity_id2, "radius": radius})

    async def entity_chamfer(self, entity_id1, entity_id2, dist1, dist2) -> CommandResult:
        return await self._dispatch("entity-chamfer", {"id1": entity_id1, "id2": entity_id2, "dist1": dist1, "dist2": dist2})

    # --- Layer operations ---

    async def layer_list(self) -> CommandResult:
        return await self._dispatch("layer-list", {})

    async def layer_create(self, name, color="white", linetype="CONTINUOUS") -> CommandResult:
        return await self._dispatch("layer-create", {"name": name, "color": color, "linetype": linetype})

    async def layer_set_current(self, name) -> CommandResult:
        return await self._dispatch("layer-set-current", {"name": name})

    async def layer_set_properties(self, name, color=None, linetype=None, lineweight=None) -> CommandResult:
        return await self._dispatch("layer-set-properties", {"name": name, "color": color, "linetype": linetype, "lineweight": lineweight})

    async def layer_freeze(self, name) -> CommandResult:
        return await self._dispatch("layer-freeze", {"name": name})

    async def layer_thaw(self, name) -> CommandResult:
        return await self._dispatch("layer-thaw", {"name": name})

    async def layer_lock(self, name) -> CommandResult:
        return await self._dispatch("layer-lock", {"name": name})

    async def layer_unlock(self, name) -> CommandResult:
        return await self._dispatch("layer-unlock", {"name": name})

    # --- Block operations ---

    async def block_list(self) -> CommandResult:
        return await self._dispatch("block-list", {})

    async def block_insert(self, name, x, y, scale=1.0, rotation=0.0, block_id=None) -> CommandResult:
        return await self._dispatch("block-insert", {"name": name, "x": x, "y": y, "scale": scale, "rotation": rotation, "block_id": block_id})

    async def block_insert_with_attributes(self, name, x, y, scale=1.0, rotation=0.0, attributes=None) -> CommandResult:
        return await self._dispatch("block-insert-with-attributes", {"name": name, "x": x, "y": y, "scale": scale, "rotation": rotation, "attributes": attributes or {}})

    async def block_get_attributes(self, entity_id) -> CommandResult:
        return await self._dispatch("block-get-attributes", {"entity_id": entity_id})

    async def block_update_attribute(self, entity_id, tag, value) -> CommandResult:
        return await self._dispatch("block-update-attribute", {"entity_id": entity_id, "tag": tag, "value": value})

    async def block_define(self, name, entities) -> CommandResult:
        return await self._dispatch("block-define", {"name": name, "entities": entities})

    # --- Annotation ---

    async def create_text(self, x, y, text, height=2.5, rotation=0.0, layer=None) -> CommandResult:
        return await self._dispatch("create-text", {"x": x, "y": y, "text": text, "height": height, "rotation": rotation, "layer": layer})

    async def create_dimension_linear(self, x1, y1, x2, y2, dim_x, dim_y) -> CommandResult:
        return await self._dispatch("create-dimension-linear", {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "dim_x": dim_x, "dim_y": dim_y})

    async def create_dimension_aligned(self, x1, y1, x2, y2, offset) -> CommandResult:
        return await self._dispatch("create-dimension-aligned", {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "offset": offset})

    async def create_dimension_angular(self, cx, cy, x1, y1, x2, y2) -> CommandResult:
        return await self._dispatch("create-dimension-angular", {"cx": cx, "cy": cy, "x1": x1, "y1": y1, "x2": x2, "y2": y2})

    async def create_dimension_radius(self, cx, cy, radius, angle) -> CommandResult:
        return await self._dispatch("create-dimension-radius", {"cx": cx, "cy": cy, "radius": radius, "angle": angle})

    async def create_leader(self, points, text) -> CommandResult:
        pts_str = ";".join(f"{p[0]},{p[1]}" for p in points)
        return await self._dispatch("create-leader", {"points_str": pts_str, "text": text})

    # --- P&ID ---

    async def pid_setup_layers(self) -> CommandResult:
        return await self._dispatch("pid-setup-layers", {})

    async def pid_insert_symbol(self, category, symbol, x, y, scale=1.0, rotation=0.0) -> CommandResult:
        return await self._dispatch("pid-insert-symbol", {"category": category, "symbol": symbol, "x": x, "y": y, "scale": scale, "rotation": rotation})

    async def pid_list_symbols(self, category) -> CommandResult:
        return await self._dispatch("pid-list-symbols", {"category": category})

    async def pid_draw_process_line(self, x1, y1, x2, y2) -> CommandResult:
        return await self._dispatch("pid-draw-process-line", {"x1": x1, "y1": y1, "x2": x2, "y2": y2})

    async def pid_connect_equipment(self, x1, y1, x2, y2) -> CommandResult:
        return await self._dispatch("pid-connect-equipment", {"x1": x1, "y1": y1, "x2": x2, "y2": y2})

    async def pid_add_flow_arrow(self, x, y, rotation=0.0) -> CommandResult:
        return await self._dispatch("pid-add-flow-arrow", {"x": x, "y": y, "rotation": rotation})

    async def pid_add_equipment_tag(self, x, y, tag, description="") -> CommandResult:
        return await self._dispatch("pid-add-equipment-tag", {"x": x, "y": y, "tag": tag, "description": description})

    async def pid_add_line_number(self, x, y, line_num, spec) -> CommandResult:
        return await self._dispatch("pid-add-line-number", {"x": x, "y": y, "line_num": line_num, "spec": spec})

    async def pid_insert_valve(self, x, y, valve_type, rotation=0.0, attributes=None) -> CommandResult:
        return await self._dispatch("pid-insert-valve", {"x": x, "y": y, "valve_type": valve_type, "rotation": rotation, "attributes": attributes or {}})

    async def pid_insert_instrument(self, x, y, instrument_type, rotation=0.0, tag_id="", range_value="") -> CommandResult:
        return await self._dispatch("pid-insert-instrument", {"x": x, "y": y, "instrument_type": instrument_type, "rotation": rotation, "tag_id": tag_id, "range_value": range_value})

    async def pid_insert_pump(self, x, y, pump_type, rotation=0.0, attributes=None) -> CommandResult:
        return await self._dispatch("pid-insert-pump", {"x": x, "y": y, "pump_type": pump_type, "rotation": rotation, "attributes": attributes or {}})

    async def pid_insert_tank(self, x, y, tank_type, scale=1.0, attributes=None) -> CommandResult:
        return await self._dispatch("pid-insert-tank", {"x": x, "y": y, "tank_type": tank_type, "scale": scale, "attributes": attributes or {}})

    # --- View ---

    async def zoom_extents(self) -> CommandResult:
        return await self._dispatch("zoom-extents", {})

    async def zoom_window(self, x1, y1, x2, y2) -> CommandResult:
        return await self._dispatch("zoom-window", {"x1": x1, "y1": y1, "x2": x2, "y2": y2})

    async def get_screenshot(self) -> CommandResult:
        if self._screenshot_provider:
            data = self._screenshot_provider.capture()
            if data:
                return CommandResult(ok=True, payload=data)
        return CommandResult(ok=False, error="Screenshot capture failed")

    # --- primitivas novas (frente 2) ---
    # O dispatcher LISP (vendor/puran-water/lisp/mcp_dispatch.lsp) nao conhece
    # estas operacoes, entao elas vao por `execute-lisp` com o mesmo corpo DXF
    # que o motor COM usa.

    def _lisp_entmakex(self, corpo: str) -> CommandResult:
        return self._dispatch("execute-lisp", {"code": corpo})

    async def create_point(self, x, y, layer=None) -> CommandResult:
        lay = layer or "0"
        corpo = ('(progn (entmakex (list (cons 0 "POINT") (cons 100 "AcDbEntity")'
                 ' (cons 8 "%s") (cons 100 "AcDbPoint") (cons 10 (list %s %s 0.0)))) T)'
                 % (lay, x, y))
        return self._lisp_entmakex(corpo)

    async def create_spline(self, fit_points, layer=None) -> CommandResult:
        if len(fit_points) < 2:
            return CommandResult(ok=False, error="spline precisa de ao menos 2 pontos")
        lay = layer or "0"
        pts = "".join(' (cons 11 (list %s %s))' % (p[0], p[1]) for p in fit_points)
        corpo = ('(progn (entmakex (list (cons 0 "SPLINE") (cons 100 "AcDbEntity")'
                 ' (cons 8 "%s") (cons 100 "AcDbSpline") (cons 41 3.0)%s)) T)' % (lay, pts))
        return self._lisp_entmakex(corpo)

    async def create_xline(self, x, y, angle_deg, layer=None) -> CommandResult:
        import math as _m
        lay = layer or "0"
        r = _m.radians(angle_deg)
        corpo = ('(progn (entmakex (list (cons 0 "XLINE") (cons 100 "AcDbEntity")'
                 ' (cons 8 "%s") (cons 100 "AcDbLine") (cons 10 (list %s %s 0.0))'
                 ' (cons 11 (list %s %s 0.0)))) T)'
                 % (lay, x, y, x + _m.cos(r), y + _m.sin(r)))
        return self._lisp_entmakex(corpo)

    async def entity_set_properties(self, entity_id, layer=None, color=None, linetype=None,
                                    lineweight=None, visible=None) -> CommandResult:
        partes = []
        if layer is not None:
            partes.append('(setq __d (subst (cons 8 "%s") (assoc 8 __d) __d))' % layer)
        if color is not None:
            partes.append('(setq __d (subst (cons 62 %s) (assoc 62 __d) __d))' % color)
        if linetype is not None:
            partes.append('(setq __d (subst (cons 6 "%s") (assoc 6 __d) __d))' % linetype)
        if lineweight is not None:
            partes.append('(setq __d (subst (cons 370 %s) (assoc 370 __d) __d))' % lineweight)
        if visible is not None:
            partes.append('(setq __d (subst (cons 60 %s) (assoc 60 __d) __d))'
                          % (0 if visible else 1))
        if not partes:
            return CommandResult(ok=False, error="nenhuma propriedade informada")
        corpo = ('(progn (setq __e (handent "%s")) (if (null __e) nil'
                 ' (progn (setq __d (entget __e)) %s (entmod __d) (entupd __e) T)))'
                 % (entity_id, " ".join(partes)))
        return self._lisp_entmakex(corpo)

    async def entity_edit_text(self, entity_id, text=None, height=None, rotation=None) -> CommandResult:
        partes = []
        if text is not None:
            partes.append('(setq __d (subst (cons 1 "%s") (assoc 1 __d) __d))' % text)
        if height is not None:
            partes.append('(setq __d (subst (cons 40 %s) (assoc 40 __d) __d))' % height)
        if rotation is not None:
            partes.append('(setq __d (subst (cons 50 %s) (assoc 50 __d) __d))' % rotation)
        if not partes:
            return CommandResult(ok=False, error="nada para alterar")
        corpo = ('(progn (setq __e (handent "%s")) (if (null __e) nil'
                 ' (progn (setq __d (entget __e)) %s (entmod __d) (entupd __e) T)))'
                 % (entity_id, " ".join(partes)))
        return self._lisp_entmakex(corpo)

    async def entity_delete_many(self, handles) -> CommandResult:
        if not handles:
            return CommandResult(ok=False, error="lista de handles vazia")
        lis = " ".join('(entdel (handent "%s"))' % h for h in handles)
        return self._lisp_entmakex("(progn %s T)" % lis)

    async def entity_array_polar(self, entity_id, count, fill_angle, center_x,
                                 center_y) -> CommandResult:
        corpo = ('(progn (setq __e (handent "%s")) (if (null __e) nil'
                 ' (progn (setq __o (vlax-ename->vla-object __e)) (setq __i 1)'
                 ' (while (< __i %d) (vla-copy __o)'
                 ' (vla-rotate (vlax-ename->vla-object (entlast))'
                 ' (vlax-3d-point (list %s %s 0.0))'
                 ' (/ (* pi %s __i) (* %d 180.0))) (setq __i (1+ __i))) T)))'
                 % (entity_id, count, center_x, center_y, fill_angle, count))
        return self._lisp_entmakex(corpo)

    async def hatch_edit(self, entity_id, pattern=None, scale=None, angle=None,
                         color=None, style=None) -> CommandResult:
        partes = []
        if pattern is not None:
            partes.append('(setq __d (subst (cons 2 "%s") (assoc 2 __d) __d))' % pattern)
        if color is not None:
            partes.append('(setq __d (subst (cons 62 %s) (assoc 62 __d) __d))' % color)
        if not partes:
            return CommandResult(ok=False, error="so pattern/color sao suportados no HATCH")
        corpo = ('(progn (setq __e (handent "%s")) (if (null __e) nil'
                 ' (progn (setq __d (entget __e)) %s (entmod __d) (entupd __e) T)))'
                 % (entity_id, " ".join(partes)))
        return self._lisp_entmakex(corpo)

    async def entity_geometry(self, entity_id: str) -> CommandResult:
        """Geometria normalizada -- mesmo LISP do motor COM."""
        corpo = (
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
            '    (cons (quote angulo_inicio) (cdr (assoc 50 __d)))'
            '    (cons (quote angulo_fim) (cdr (assoc 51 __d)))))))'
            % entity_id
        )
        return self._lisp_entmakex(corpo)

    async def create_table(self, x: float, y: float, rows: list[list[str]],
                           headers: list[str] | None = None,
                           column_widths: list[float] | None = None,
                           row_height: float = 2.5,
                           text_height: float = 2.5,
                           title: str | None = None,
                           layer: str | None = None) -> CommandResult:
        """Cria uma tabela usando LISP TABLE."""
        lay = _q(layer or "0")
        num_cols = len(headers or rows[0]) if rows else 0
        num_rows = len(rows) + (1 if headers else 0)
        
        if not num_cols or not num_rows:
            return CommandResult(ok=False, error="tabela vazia")
        
        col_w = column_widths or [10.0] * num_cols
        
        lisp = (
            '(setq __tab (vla-addtable (vla-get-modelspace (vla-get-activedocument (vlax-get-acad-object))) "%s" %s %s))'
            % (lay, x, y)
        )
        r = self._aval(lisp)
        if not r.ok:
            return r
        return CommandResult(ok=True, payload={"handle": "TODO", "type": "TABLE"})
