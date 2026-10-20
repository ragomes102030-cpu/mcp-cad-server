# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import traceback

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import pythoncom
import win32com.client as wc

pythoncom.CoInitialize()

print("=" * 70)
print("ROTA A: GetActiveObject dinamico")
print("=" * 70)
app = wc.GetActiveObject("AutoCAD.Application.25")
print("app:", type(app).__name__, app.Name)


def tenta(rotulo, fn):
    try:
        v = fn()
        print("  OK  %-28s -> %r" % (rotulo, str(v)[:70]))
        return v
    except Exception as e:
        print("  ERR %-28s -> %s: %s" % (rotulo, type(e).__name__, e))
        return None


docs = tenta("app.Documents", lambda: app.Documents)
if docs is not None:
    print("      repr(docs) =", repr(docs))
    tenta("docs.Count", lambda: docs.Count)
    tenta("docs.Item(0).Name", lambda: docs.Item(0).Name)

doc = tenta("app.ActiveDocument", lambda: app.ActiveDocument)
if doc is not None:
    print("      repr(doc) =", repr(doc))
    tenta("doc.Name", lambda: doc.Name)
    ms = tenta("doc.ModelSpace", lambda: doc.ModelSpace)
    if ms is not None:
        tenta("ModelSpace.Count", lambda: ms.Count)

print()
print("=" * 70)
print("ROTA B: gencache.EnsureDispatch (binding precoce)")
print("=" * 70)
import win32com.client.gencache as gencache

try:
    app2 = gencache.EnsureDispatch("AutoCAD.Application.25")
    print("app2:", type(app2).__name__, "Name=", app2.Name, "Version=", app2.Version)
    tenta("app2.Documents.Count", lambda: app2.Documents.Count)
    tenta("app2.ActiveDocument.Name", lambda: app2.ActiveDocument.Name)
    ms2 = tenta("app2.ActiveDocument.ModelSpace", lambda: app2.ActiveDocument.ModelSpace)
    if ms2 is not None:
        tenta("ModelSpace.Count", lambda: ms2.Count)
        tenta("ModelSpace.Item(0).ObjectName", lambda: ms2.Item(0).ObjectName)
except Exception:
    traceback.print_exc()

print()
print("=" * 70)
print("ROTA C: buscar o typelib registrado")
print("=" * 70)
import win32com.client.makepy as makepy

try:
    print("typelibs:", list(makepy.GetTypeLibsOfProgID("AutoCAD.Application.25"))[:3])
except Exception:
    traceback.print_exc()
