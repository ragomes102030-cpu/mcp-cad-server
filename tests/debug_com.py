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

app = wc.GetActiveObject("AutoCAD.Application.25")
print("app        =", type(app), app)

try:
    print("app.Name   =", app.Name)
except Exception:
    traceback.print_exc()

try:
    print("app.Version=", app.Version)
except Exception:
    traceback.print_exc()

docs = app.Documents
print("docs       =", type(docs), "count=", docs.Count)

doc = app.ActiveDocument
print("doc        =", type(doc), repr(doc))
print("doc._oleobj_ =", doc._oleobj_ if hasattr(doc, "_oleobj_") else "n/a")

for attr in ("Name", "FullName", "ModelSpace"):
    try:
        v = getattr(doc, attr)
        print("doc.%-10s = %r" % (attr, str(v)[:80]))
    except Exception as e:
        print("doc.%-10s ERRO: %s" % (attr, e))

# tentativa alternativa: pegar o documento pela colecao
try:
    d2 = docs.Item(0)
    print("docs.Item(0).Name =", d2.Name)
except Exception:
    traceback.print_exc()
