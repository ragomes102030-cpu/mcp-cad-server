using System.Collections.Generic;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;
using AcApp = Autodesk.AutoCAD.ApplicationServices.Core.Application;

namespace CadMcpBridge
{
    /// <summary>
    /// Edicao por GEOMETRIA, sem comando e sem prompt.
    ///
    /// Por que existe: TRIM, EXTEND e FILLET nao sao metodos de API no COM e, como
    /// comando, dependem de selecao na tela. As referencias que usam `SendCommand`
    /// com `handent` funcionam, mas mantem a ponte refem de foco, eco e do estado
    /// do comando. Aqui a conta e' feita com a matematica do proprio AutoCAD
    /// (IntersectWith + GetClosestPointTo), dentro de uma Transaction e do thread
    /// principal (via Ponte.NoContexto). Contrato alinhado com o do autocad-mcp-pro
    /// 1.6.0 para que o agente possa trocar de motor sem mudar o prompt.
    ///
    /// Convencao de retorno: erro de dado (handle sumido, retas paralelas) vira
    /// ok=false com motivo; nada lanca para fora -- o agente decide o que fazer.
    /// </summary>
    internal static class Geometria
    {
        /// <summary>
        /// ENCURTA a reta alvo ate' a reta de corte, mantendo o lado que contem
        /// (keep_x, keep_y). Equivalente ao TRIM com "implied extend": o corte e'
        /// tratado como reta infinita. Somente LINE+LINE, como no padrao.
        /// </summary>
        internal static object Trim(
            Dictionary<string, object> op, Transaction tr, Database db)
        {
            var hAlvo = Texto(op, "alvo");
            var hCorte = Texto(op, "corte");
            var idAlvo = ObterId(db, hAlvo);
            var idCorte = ObterId(db, hCorte);
            if (idAlvo.IsNull) return Falha("alvo nao encontrado");
            if (idCorte.IsNull) return Falha("corte nao encontrado");
            if (idAlvo == idCorte) return Falha("alvo e corte nao podem ser a mesma reta");

            var keep = Ponto(op, "keep");
            if (keep == null) return Falha("trim precisa de 'keep' (ponto no lado que fica)");

            var alvo = tr.GetObject(idAlvo, OpenMode.ForWrite, false, true) as Line;
            var corte = tr.GetObject(idCorte, OpenMode.ForRead, false, true) as Line;
            if (alvo == null || corte == null)
                return Falha("trim so' trabalha com duas retas (LINE)");

            var x = IntersecaoInfinitas(alvo, corte);
            if (x == null) return Falha("as retas sao paralelas ou coincidentes");

            // `keep` fica no trecho que sobrevive: o extremo oposto e' o que se move
            // ate' a intersecao. Se keep esta mais perto do inicio, o inicio fica.
            if (keep.Value.DistanceTo(alvo.StartPoint) <= keep.Value.DistanceTo(alvo.EndPoint))
                alvo.EndPoint = x.Value;
            else
                alvo.StartPoint = x.Value;

            return new { ok = true, op = "trim", handle = hAlvo, corte = hCorte };
        }

        /// <summary>
        /// ESTENDE a reta alvo ate' a reta de limite. Se `ponto` vier, e' o extremo
        /// movido (o mais proximo dele); sem ele, escolhe o extremo mais proximo do
        /// meio do limite -- a heuristica "auto" do padrao.
        /// </summary>
        internal static object Extend(
            Dictionary<string, object> op, Transaction tr, Database db)
        {
            var hAlvo = Texto(op, "alvo");
            var hLimite = Texto(op, "limite");
            var idAlvo = ObterId(db, hAlvo);
            var idLim = ObterId(db, hLimite);
            if (idAlvo.IsNull) return Falha("alvo nao encontrado");
            if (idLim.IsNull) return Falha("limite nao encontrado");
            if (idAlvo == idLim) return Falha("alvo e limite nao podem ser a mesma reta");

            var alvo = tr.GetObject(idAlvo, OpenMode.ForWrite, false, true) as Line;
            var limite = tr.GetObject(idLim, OpenMode.ForRead, false, true) as Line;
            if (alvo == null || limite == null)
                return Falha("extend so' trabalha com duas retas (LINE)");

            var x = IntersecaoInfinitas(alvo, limite);
            if (x == null) return Falha("as retas sao paralelas: nada a estender");

            var ponto = Ponto(op, "ponto");
            bool peloInicio;
            if (ponto != null)
            {
                peloInicio = ponto.Value.DistanceTo(alvo.StartPoint)
                             <= ponto.Value.DistanceTo(alvo.EndPoint);
            }
            else
            {
                var meio = limite.StartPoint + (limite.EndPoint - limite.StartPoint) * 0.5;
                peloInicio = meio.DistanceTo(alvo.StartPoint) <= meio.DistanceTo(alvo.EndPoint);
            }

            // so' estende se a intersecao estiver alem do extremo escolhido
            double t = ParametroDeExtensao(alvo, x.Value, peloInicio);
            if (t < 0) return Falha("o alvo ja' alcanca o limite antes desse extremo");

            if (peloInicio) alvo.StartPoint = x.Value;
            else alvo.EndPoint = x.Value;

            return new
            {
                ok = true,
                op = "extend",
                handle = hAlvo,
                limite = hLimite,
                extremo = peloInicio ? "inicio" : "fim",
            };
        }

        /// <summary>
        /// ARREDONDA o canto entre duas retas com um arco tangente de raio dado,
        /// encurtando as duas ate' os pontos de tangencia (trim=true). Somente
        /// LINE+LINE, como no padrao.
        /// </summary>
        internal static object Fillet(
            Dictionary<string, object> op, Transaction tr, Database db)
        {
            var h1 = Texto(op, "h1");
            var h2 = Texto(op, "h2");
            double raio = Numero(op, "raio", 0);
            if (raio < 0) return Falha("fillet precisa de 'raio' >= 0");
            bool trim = Booleano(op, "trim", true);

            var id1 = ObterId(db, h1);
            var id2 = ObterId(db, h2);
            if (id1.IsNull || id2.IsNull) return Falha("h1/h2 nao encontrados");
            if (id1 == id2) return Falha("h1 e h2 nao podem ser a mesma reta");

            var l1 = tr.GetObject(id1, OpenMode.ForWrite, false, true) as Line;
            var l2 = tr.GetObject(id2, OpenMode.ForWrite, false, true) as Line;
            if (l1 == null || l2 == null) return Falha("fillet so' trabalha com duas retas (LINE)");

            var v = IntersecaoInfinitas(l1, l2);
            if (v == null) return Falha("as retas sao paralelas ou coincidentes");

            if (raio == 0)
            {
                // canto vivo: junta as duas no vertice, sem arco
                JuntarNoVertice(l1, v.Value);
                JuntarNoVertice(l2, v.Value);
                return new { ok = true, op = "fillet", h1, h2, raio, arco_handle = (string)null };
            }

            var p1 = Ponto(op, "p1") ?? l1.GetClosestPointTo(v.Value, false);
            var p2 = Ponto(op, "p2") ?? l2.GetClosestPointTo(v.Value, false);

            var dir1 = l1.GetFirstDerivative(l1.GetParameterAtPoint(p1)).GetNormal();
            var dir2 = l2.GetFirstDerivative(l2.GetParameterAtPoint(p2)).GetNormal();

            // aponta o vetor unitario de cada reta na direcao do lado que fica
            var u1 = ApontarPara(dir1, p1 - v.Value);
            var u2 = ApontarPara(dir2, p2 - v.Value);

            double ang = u1.GetAngleTo(u2);           // 0..pi
            if (ang < 1e-9 || Math.Abs(ang - Math.PI) < 1e-9)
                return Falha("as retas nao formam canto");

            double half = ang / 2.0;
            double dist = raio / Math.Tan(half);       // vertice -> tangencia

            var t1 = v.Value + u1 * dist;
            var t2 = v.Value + u2 * dist;

            var centro = v.Value + (u1 + u2).GetNormal() * (raio / Math.Sin(half));

            if (trim)
            {
                var pontoContrario1 = EnfraquecerExtremo(l1, t1);
                var pontoContrario2 = EnfraquecerExtremo(l2, t2);
                SubstituirExtremos(l1, t1, pontoContrario1);
                SubstituirExtremos(l2, t2, pontoContrario2);
            }

            // arco de t1 a t2 pelo lado de fora do canto
            double a1 = Math.Atan2(t1.Y - centro.Y, t1.X - centro.X);
            double a2 = Math.Atan2(t2.Y - centro.Y, t2.X - centro.X);
            var arco = new Arc(centro, raio, OrdenarAngulo(centro, a1, a2, t1, t2, v.Value, 1),
                               OrdenarAngulo(centro, a1, a2, t1, t2, v.Value, 2));
            arco.Layer = l1.Layer;
            var espaco = (BlockTableRecord)tr.GetObject(db.CurrentSpaceId, OpenMode.ForWrite);
            espaco.AppendEntity(arco);
            tr.AddNewlyCreatedDBObject(arco, true);

            return new
            {
                ok = true,
                op = "fillet",
                h1,
                h2,
                raio,
                arco_handle = arco.Handle.ToString(),
            };
        }

        // ------------------------------------------------------------------ apoio

        /// <summary>Intersecao das retas tratadas como infinitas (ou null se paralelas).</summary>
        private static Point3d? IntersecaoInfinitas(Line a, Line b)
        {
            var d1 = a.Delta;
            var d2 = b.Delta;
            var cruz = d1.CrossProduct(d2);
            if (cruz.Length < 1e-12) return null;
            var w = b.StartPoint - a.StartPoint;
            double s = w.CrossProduct(d2).DotProduct(cruz) / cruz.DotProduct(cruz);
            return a.StartPoint + d1 * s;
        }

        /// <summary>
        /// Parametro da intersecao relativo ao extremo: >0 significa "alem do
        /// extremo", ou seja, ha' o que estender naquele lado.
        /// </summary>
        private static double ParametroDeExtensao(Line reta, Point3d x, bool peloInicio)
        {
            var comprimento = (reta.EndPoint - reta.StartPoint).Length;
            if (comprimento < 1e-12) return 0;
            double proj = peloInicio
                ? (reta.StartPoint - x).DotProduct((reta.EndPoint - reta.StartPoint) / comprimento)
                : (x - reta.EndPoint).DotProduct((reta.EndPoint - reta.StartPoint) / comprimento);
            return proj;
        }

        private static Vector3d ApontarPara(Vector3d dir, Vector3d alvo)
            => dir.DotProduct(alvo) >= 0 ? dir : -dir;

        private static Point3d EnfraquecerExtremo(Line reta, Point3d tangencia)
            => tangencia.DistanceTo(reta.StartPoint) <= tangencia.DistanceTo(reta.EndPoint)
                ? reta.EndPoint : reta.StartPoint;

        private static void SubstituirExtremos(Line reta, Point3d tangencia, Point3d contrario)
        {
            if (tangencia.DistanceTo(reta.StartPoint) <= tangencia.DistanceTo(reta.EndPoint))
            { reta.StartPoint = tangencia; reta.EndPoint = contrario; }
            else
            { reta.EndPoint = tangencia; reta.StartPoint = contrario; }
        }

        private static void JuntarNoVertice(Line reta, Point3d vertice)
        {
            if (vertice.DistanceTo(reta.StartPoint) <= vertice.DistanceTo(reta.EndPoint))
                reta.StartPoint = vertice;
            else
                reta.EndPoint = vertice;
        }

        /// <summary>
        /// Escolhe qual angulo usar como inicio/fim do arco, de modo que ele cubra o
        /// lado de fora do canto (o arco curto entre t1 e t2 que nao passa pelo
        /// vertice). `qual` = 1 devolve o inicio, 2 o fim.
        /// </summary>
        private static double OrdenarAngulo(
            Point3d centro, double a1, double a2, Point3d t1, Point3d t2, Point3d vertice, int qual)
        {
            double vAng = Math.Atan2(vertice.Y - centro.Y, vertice.X - centro.X);
            bool arcoNormal = !EntreAngulo(vAng, a1, a2);
            if (qual == 1) return a1;
            return arcoNormal ? a2 : a1 + Normalizar(a2 - a1);
        }

        private static bool EntreAngulo(double ang, double a, double b)
        {
            double span = Normalizar(b - a);
            return Normalizar(ang - a) < span - 1e-12;
        }

        private static double Normalizar(double a)
        {
            const double tau = 2.0 * Math.PI;
            a %= tau;
            return a < 0 ? a + tau : a;
        }

        private static ObjectId ObterId(Database db, string handleHex)
        {
            if (string.IsNullOrWhiteSpace(handleHex)) return ObjectId.Null;
            long valor = Convert.ToInt64(handleHex, 16);
            return db.TryGetObjectId(new Handle(valor), out ObjectId id) ? id : ObjectId.Null;
        }

        private static string Texto(Dictionary<string, object> d, string k)
            => d != null && d.TryGetValue(k, out var v) && v != null ? Convert.ToString(v) : null;

        private static double Numero(Dictionary<string, object> d, string k, double padrao)
            => d != null && d.TryGetValue(k, out var v) && v != null ? Convert.ToDouble(v) : padrao;

        private static bool Booleano(Dictionary<string, object> d, string k, bool padrao)
            => d != null && d.TryGetValue(k, out var v) && v is bool b ? b : padrao;

        private static Point3d? Ponto(Dictionary<string, object> d, string k)
        {
            if (d == null || !d.TryGetValue(k, out var v) || v is not System.Collections.IEnumerable seq)
                return null;
            var vals = new List<double>();
            foreach (var item in seq) vals.Add(Convert.ToDouble(item));
            return vals.Count >= 2 ? new Point3d(vals[0], vals[1], vals.Count > 2 ? vals[2] : 0) : null;
        }

        private static object Falha(string motivo) => new { ok = false, erro = motivo };
    }
}
