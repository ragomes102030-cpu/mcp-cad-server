using System.Diagnostics;
using System.Text;
using System.Threading;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Geometry;
using AcApp = Autodesk.AutoCAD.ApplicationServices.Core.Application;

namespace CadMcpBridge
{
    /// <summary>
    /// Operacoes da ponte. Tudo que toca o documento roda no thread principal do
    /// AutoCAD via <see cref="Fila"/> (evento Application.Idle), com prazo.
    /// </summary>
    internal static class Ponte
    {
        private const int PrazoPadraoMs = 20000;

        internal static T NoContexto<T>(Func<T> trabalho)
            => Fila.NoContexto(trabalho, PrazoPadraoMs);

        internal static T NoContexto<T>(Func<T> trabalho, int timeoutMs)
            => Fila.NoContexto(trabalho, timeoutMs);

        internal static object Info()
        {
            return NoContexto(() =>
            {
                var doc = AcApp.DocumentManager.MdiActiveDocument;
                if (doc == null) return (object)new { ok = true, vazio = true, produto = "CadMcpBridge" };
                var db = doc.Database;
                return new
                {
                    ok = true,
                    produto = "CadMcpBridge",
                    versao = "1.0",
                    acad = AcApp.Version.ToString(),
                    desenho = doc.Name,
                    insunits = GetVar("INSUNITS"),
                    filedia = GetVar("FILEDIA"),
                    cmddia = GetVar("CMDDIA"),
                };
            });
        }

        private static object GetVar(string nome)
        {
            try { return AcApp.GetSystemVariable(nome); }
            catch { return null; }
        }

        /// <summary>
        /// Roda um comando do AutoCAD dentro do processo e espera terminar.
        /// Com FILEDIA/CMDDIA em 0, nada abre caixa de dialogo.
        /// `pontos` entra como Point3d (escolha implicita / vertices).
        /// </summary>
        internal static object Exec(string comando, double[][] pontos, bool confirmar)
        {
            var sw = Stopwatch.StartNew();
            string desenho = null;
            string erro = null;

            NoContexto(() =>
            {
                var doc = AcApp.DocumentManager.MdiActiveDocument;
                if (doc == null) { erro = "nenhum desenho aberto"; return false; }

                desenho = doc.Name;
                object filedia = GetVar("FILEDIA");
                object cmddia = GetVar("CMDDIA");
                SetVar("FILEDIA", 0);
                SetVar("CMDDIA", 0);

                // SendStringToExecute, nao Editor.Command.
                // Editor.Command e sincrono: se a entrada acabar antes da hora (TRIM
                // esperando a proxima selecao), ele NAO volta - trava a thread
                // principal e o AutoCAD inteiro para de responder, inclusive o COM.
                // Ja aconteceu. SendStringToExecute devolve na hora e o comando roda
                // sozinho, como se fosse digitado.
                doc.SendStringToExecute(MontarTexto(comando, pontos), true, false, true);
                RestaurarQuandoOcioso(filedia, cmddia);
                return true;
            });

            if (erro != null) return new { ok = false, erro };

            if (!confirmar)
                return new
                {
                    ok = true,
                    comando,
                    desenho,
                    duracao_ms = sw.ElapsedMilliseconds,
                    aviso = "enviado; o comando termina sozinho (assincrono)",
                };

            return Confirmar(comando, desenho, sw);
        }

        /// <summary>
        /// Espera o CMDACTIVE voltar a zero e devolve o ultimo prompt. Cada leitura
        /// passa pela Fila com prazo curto: enquanto o comando roda a thread
        /// principal esta ocupada, entao TimeoutException e' esperado e nao fatal.
        /// </summary>
        private static object Confirmar(string comando, string desenho, Stopwatch sw)
        {
            string lastprompt = null;
            int cmdactive = -1;
            bool concluiu = false;
            var limite = DateTime.UtcNow.AddMilliseconds(PrazoPadraoMs);
            Thread.Sleep(250);

            while (DateTime.UtcNow < limite)
            {
                try
                {
                    var estado = Fila.NoContexto(() => (
                        cmd: Convert.ToInt32(AcApp.GetSystemVariable("CMDACTIVE")),
                        prompt: Convert.ToString(AcApp.GetSystemVariable("LASTPROMPT"))
                    ), 500);
                    cmdactive = estado.cmd;
                    lastprompt = estado.prompt;
                    if (cmdactive == 0 && sw.ElapsedMilliseconds > 400)
                    {
                        concluiu = true;
                        break;
                    }
                }
                catch (TimeoutException)
                {
                    // comando em andamento: a thread principal nao esta ociosa
                }
                Thread.Sleep(120);
            }

            return new
            {
                ok = true,
                comando,
                desenho,
                concluiu,
                cmdactive,
                lastprompt,
                duracao_ms = sw.ElapsedMilliseconds,
            };
        }

        private static void RestaurarQuandoOcioso(object filedia, object cmddia)
        {
            var t = new Thread(() =>
            {
                for (int i = 0; i < 600; i++)
                {
                    bool ocioso;
                    try
                    {
                        ocioso = NoContexto(
                            () => Convert.ToInt32(AcApp.GetSystemVariable("CMDACTIVE")) == 0, 500);
                    }
                    catch
                    {
                        ocioso = false;
                    }
                    if (ocioso)
                    {
                        try
                        {
                            NoContexto(() =>
                            {
                                SetVar("FILEDIA", filedia);
                                SetVar("CMDDIA", cmddia);
                                return true;
                            }, 3000);
                        }
                        catch { }
                        return;
                    }
                    Thread.Sleep(100);
                }
            })
            { IsBackground = true };
            t.Start();
        }

        /// <summary>
        /// Transforma tokens + pontos no texto que o usuario digitaria.
        /// "ENTER" e cada token viram uma linha (linha = Enter no AutoCAD).
        /// </summary>
        private static string MontarTexto(string comando, double[][] pontos)
        {
            var ci = System.Globalization.CultureInfo.InvariantCulture;
            var sb = new StringBuilder();
            var partes = (comando ?? "").Split(
                new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
            var coords = new List<string>();
            if (pontos != null)
            {
                foreach (var p in pontos)
                {
                    if (p == null || p.Length < 2) continue;
                    coords.Add(p.Length > 2 && Math.Abs(p[2]) > 1e-9
                        ? string.Format(ci, "{0},{1},{2}", p[0], p[1], p[2])
                        : string.Format(ci, "{0},{1}", p[0], p[1]));
                }
            }
            bool marcador = false;
            foreach (var parte in partes)
            {
                if (parte == "@PONTOS")
                {
                    foreach (var c in coords) sb.Append(c).Append('\n');
                    marcador = true;
                    continue;
                }
                if (parte == "ENTER") { sb.Append('\n'); continue; }
                sb.Append(parte).Append('\n');
            }
            if (!marcador) foreach (var c in coords) sb.Append(c).Append('\n');
            return sb.ToString();
        }

        private static void SetVar(string nome, object valor)
        {
            try { if (valor != null) AcApp.SetSystemVariable(nome, valor); }
            catch { /* variavel read-only em algum contexto */ }
        }

        /// <summary>
        /// Transacao: mexe em entidades por handle, com undo do AutoCAD.
        /// ops: [{op:"erase"|"move"|"copy"|"rotacao"|"prop", handle:"1A2", ...}]
        /// </summary>
        internal static object Transacao(IEnumerable<Dictionary<string, object>> ops)
        {
            return NoContexto(() =>
            {
                var doc = AcApp.DocumentManager.MdiActiveDocument;
                if (doc == null) return (object)new { ok = false, erro = "nenhum desenho aberto" };
                var db = doc.Database;
                var feitas = new List<object>();
                using (var tr = db.TransactionManager.StartTransaction())
                {
                    foreach (var op in ops)
                    {
                        string tipo = Texto(op, "op");
                        string handle = Texto(op, "handle");
                        using (var lck = AcApp.DocumentManager.MdiActiveDocument?.LockDocument())
                        {
                        try
                        {
                            // Edicao por geometria: nao e' por handle unico, entao sai
                            // antes da busca padrao. Usa a matematica do AutoCAD dentro
                            // desta mesma transacao (undo + consistencia).
                            if (tipo == "trim" || tipo == "extend" || tipo == "fillet")
                            {
                                object r = tipo switch
                                {
                                    "trim" => Geometria.Trim(op, tr, db),
                                    "extend" => Geometria.Extend(op, tr, db),
                                    _ => Geometria.Fillet(op, tr, db),
                                };
                                feitas.Add(r);
                                continue;
                            }

                            var id = ObterId(db, handle);
                            if (id.IsNull)
                            {
                                feitas.Add(new { handle, op = tipo, ok = false, erro = "handle nao encontrado" });
                                continue;
                            }
                            var ent = (Entity)tr.GetObject(id, OpenMode.ForWrite, false, true);
                            switch (tipo)
                            {
                                case "erase":
                                    ent.Erase();
                                    break;
                                case "move":
                                    ent.TransformBy(Matrix3d.Displacement(Desloc(op)));
                                    break;
                                case "copy":
                                    var clone = (Entity)ent.Clone();
                                    clone.TransformBy(Matrix3d.Displacement(Desloc(op)));
                                    var btr = (BlockTableRecord)tr.GetObject(db.CurrentSpaceId, OpenMode.ForWrite);
                                    var novo = btr.AppendEntity((Entity)clone);
                                    tr.AddNewlyCreatedDBObject((DBObject)clone, true);
                                    feitas.Add(new { handle, op = tipo, ok = true, novo_handle = novo.Handle.ToString() });
                                    continue;
                                case "rotacao":
                                    double ang = Numero(op, "angulo", 0) * Math.PI / 180.0;
                                    var centro = Ponto(op, "centro") ?? Point3d.Origin;
                                    ent.TransformBy(Matrix3d.Rotation(ang, Vector3d.ZAxis, centro));
                                    break;
                                case "prop":
                                    var prop = ent.GetType().GetProperty(Texto(op, "nome"));
                                    if (prop == null)
                                    {
                                        feitas.Add(new { handle, op = tipo, ok = false, erro = "propriedade inexistente" });
                                        continue;
                                    }
                                    prop.SetValue(ent, Convert.ChangeType(
                                        Convert.ToString(op["valor"],
                                            System.Globalization.CultureInfo.InvariantCulture),
                                        prop.PropertyType));
                                    break;
                                default:
                                    feitas.Add(new { handle, op = tipo, ok = false, erro = "op desconhecida" });
                                    continue;
                            }
                            feitas.Add(new { handle, op = tipo, ok = true });
                        }
                        catch (System.Exception ex)
                        {
                            feitas.Add(new { handle, op = tipo, ok = false, erro = ex.Message });
                        }
                        }
                    }
                    tr.Commit();
                }
                return (object)new { ok = true, resultados = feitas };
            });
        }

        private static ObjectId ObterId(Database db, string handleHex)
        {
            if (string.IsNullOrWhiteSpace(handleHex)) return ObjectId.Null;
            long valor = Convert.ToInt64(handleHex, 16);
            return db.TryGetObjectId(new Handle(valor), out ObjectId id) ? id : ObjectId.Null;
        }

        private static string Texto(Dictionary<string, object> d, string k)
            => d.TryGetValue(k, out var v) ? Convert.ToString(v) : null;

        private static double Numero(Dictionary<string, object> d, string k, double padrao)
            => d.TryGetValue(k, out var v) && v != null ? Convert.ToDouble(v) : padrao;

        private static Point3d? Ponto(Dictionary<string, object> d, string k)
        {
            if (!d.TryGetValue(k, out var v) || v is not System.Collections.IEnumerable seq) return null;
            var vals = new List<double>();
            foreach (var item in seq) vals.Add(Convert.ToDouble(item));
            return vals.Count >= 2 ? new Point3d(vals[0], vals[1], vals.Count > 2 ? vals[2] : 0) : null;
        }

        private static Vector3d Desloc(Dictionary<string, object> op)
        {
            var de = Ponto(op, "de") ?? Point3d.Origin;
            var para = Ponto(op, "para") ?? Point3d.Origin;
            return para - de;
        }
    }
}
