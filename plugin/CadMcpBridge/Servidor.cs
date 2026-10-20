using System.Net;
using System.Net.Sockets;
using System.Text;

namespace CadMcpBridge
{
    /// <summary>
    /// Ponte TCP local: uma linha JSON por requisicao, uma linha de resposta.
    /// 127.0.0.1 apenas, com token gerado a cada carga (arquivo em %TEMP%).
    /// Sem HTTP, sem dependencia externa, sem porta aberta para a rede.
    /// </summary>
    internal static class Servidor
    {
        private static TcpListener _listener;
        private static Thread _thread;
        private static string _token;
        private static int _porta;

        internal static string ArquivoInfo =>
            Path.Combine(Path.GetTempPath(), "cad_mcp_bridge.json");
        internal static string ArquivoLog =>
            Path.Combine(Path.GetTempPath(), "cad_mcp_bridge.log");

        internal static void Iniciar()
        {
            if (_listener != null) return;
            _token = Guid.NewGuid().ToString("N");

            for (int p = 8765; p < 8790; p++)
            {
                try
                {
                    var l = new TcpListener(IPAddress.Loopback, p);
                    l.Start();
                    _listener = l;
                    _porta = p;
                    break;
                }
                catch (SocketException) { /* porta ocupada: tenta a proxima */ }
            }
            if (_listener == null)
            {
                Log("nenhuma porta livre entre 8765 e 8789");
                return;
            }

            File.WriteAllText(ArquivoInfo, Json.Escrever(new
            {
                porta = _porta,
                token = _token,
                pid = Environment.ProcessId,
                quando = DateTime.Now.ToString("o"),
                versao = "1.0",
            }));

            _thread = new Thread(Loop) { IsBackground = true, Name = "CadMcpBridge" };
            _thread.Start();
            Log("ponte no ar em 127.0.0.1:" + _porta);
        }

        internal static void Parar()
        {
            try { _listener?.Stop(); } catch { }
            _listener = null;
            try { if (File.Exists(ArquivoInfo)) File.Delete(ArquivoInfo); } catch { }
        }

        internal static string Estado()
            => _listener == null ? "parada" : $"ativa em 127.0.0.1:{_porta}";

        private static void Loop()
        {
            while (_listener != null)
            {
                try
                {
                    using var cliente = _listener.AcceptTcpClient();
                    cliente.ReceiveTimeout = 20000;
                    using var fluxo = cliente.GetStream();
                    using var leitor = new StreamReader(fluxo, new UTF8Encoding(false));
                    using var escritor = new StreamWriter(fluxo, new UTF8Encoding(false)) { AutoFlush = true };
                    string linha = leitor.ReadLine();
                    if (string.IsNullOrWhiteSpace(linha)) continue;
                    escritor.WriteLine(Responder(linha));
                }
                catch (System.Exception ex)
                {
                    Log("loop: " + ex.Message);
                }
            }
        }

        private static string Responder(string linha)
        {
            try
            {
                var raiz = Json.LerObjeto(linha);
                string token = Texto(raiz, "token");
                if (!string.Equals(token, _token, StringComparison.Ordinal))
                    return Json.Escrever(new { ok = false, erro = "token invalido" });

                string metodo = Texto(raiz, "metodo") ?? "";
                var args = Objeto(raiz, "args") ?? new Dictionary<string, object>();

                object resultado = metodo switch
                {
                    "ping" => Ponte.Info(),
                    "info" => Ponte.Info(),
                    "exec" => Ponte.Exec(Texto(args, "comando") ?? "", Pontos(args), Booleano(args, "confirmar")),
                    "transaction" => Ponte.Transacao(Operacoes(args)),
                    _ => new { ok = false, erro = "metodo desconhecido: " + metodo },
                };
                return Json.Escrever(resultado);
            }
            catch (System.Exception ex)
            {
                Log("resposta: " + ex);
                return Json.Escrever(new { ok = false, erro = ex.Message, tipo = ex.GetType().Name });
            }
        }

        internal static string Texto(Dictionary<string, object> d, string chave)
            => d != null && d.TryGetValue(chave, out var v) && v != null
                   ? Convert.ToString(v, System.Globalization.CultureInfo.InvariantCulture)
                   : null;

        private static bool Booleano(Dictionary<string, object> d, string chave)
            => d != null && d.TryGetValue(chave, out var v) && v is bool b && b;

        private static Dictionary<string, object> Objeto(Dictionary<string, object> d, string chave)
            => d != null && d.TryGetValue(chave, out var v) ? v as Dictionary<string, object> : null;

        private static List<object> Lista(Dictionary<string, object> d, string chave)
            => d != null && d.TryGetValue(chave, out var v) ? v as List<object> : null;

        private static double[][] Pontos(Dictionary<string, object> args)
        {
            var arr = Lista(args, "pontos");
            if (arr == null) return Array.Empty<double[]>();
            var saida = new List<double[]>();
            foreach (var item in arr)
            {
                if (item is not List<object> par) continue;
                var vals = new List<double>();
                foreach (var n in par) vals.Add(Convert.ToDouble(n, System.Globalization.CultureInfo.InvariantCulture));
                if (vals.Count >= 2) saida.Add(vals.ToArray());
            }
            return saida.ToArray();
        }

        private static List<Dictionary<string, object>> Operacoes(Dictionary<string, object> args)
        {
            var arr = Lista(args, "ops");
            var saida = new List<Dictionary<string, object>>();
            if (arr == null) return saida;
            foreach (var item in arr)
                if (item is Dictionary<string, object> d) saida.Add(d);
            return saida;
        }

        internal static void Log(string msg)
        {
            try { File.AppendAllText(ArquivoLog, DateTime.Now.ToString("HH:mm:ss") + "  " + msg + "\n"); }
            catch { }
        }
    }
}
