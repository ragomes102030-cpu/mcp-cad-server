using System.Collections;
using System.Globalization;
using System.Text;

namespace CadMcpBridge
{
    /// <summary>
    /// JSON minimo, escrito a mao, de proposito.
    /// O AutoCAD 2025 roda .NET 8 mas NAO traz System.Text.Json junto do acad.exe
    /// (so existe em BFMigrator). Usar o namespace oficial fazia a DLL falhar em
    /// silencio na carga: a excecao estourava no JIT de Iniciar() e morria no
    /// try/catch do Initialize. Com isto a ponte nao depende de nada.
    /// Cobre o que o protocolo usa: objeto, lista, texto, numero, booleano, nulo.
    /// </summary>
    internal static class Json
    {
        // ---------- escrever ----------

        internal static string Escrever(object valor)
        {
            var sb = new StringBuilder(256);
            Escreve(sb, valor);
            return sb.ToString();
        }

        private static void Escreve(StringBuilder sb, object v)
        {
            switch (v)
            {
                case null: sb.Append("null"); return;
                case string s: Texto(sb, s); return;
                case bool b: sb.Append(b ? "true" : "false"); return;
                case char c: Texto(sb, c.ToString()); return;
                case double d: sb.Append(d.ToString("R", CultureInfo.InvariantCulture)); return;
                case float f: sb.Append(f.ToString("R", CultureInfo.InvariantCulture)); return;
                case decimal m: sb.Append(m.ToString(CultureInfo.InvariantCulture)); return;
                case int _:
                case long _:
                case short _:
                case byte _:
                case uint _:
                case ulong _:
                    sb.Append(Convert.ToString(v, CultureInfo.InvariantCulture)); return;
                case Enum e: Texto(sb, e.ToString()); return;
            }

            if (v is IDictionary mapa)
            {
                sb.Append('{');
                bool primeiro = true;
                foreach (DictionaryEntry par in mapa)
                {
                    if (!primeiro) sb.Append(',');
                    primeiro = false;
                    Texto(sb, Convert.ToString(par.Key, CultureInfo.InvariantCulture));
                    sb.Append(':');
                    Escreve(sb, par.Value);
                }
                sb.Append('}');
                return;
            }

            if (v is IEnumerable seq)
            {
                sb.Append('[');
                bool primeiro = true;
                foreach (var item in seq)
                {
                    if (!primeiro) sb.Append(',');
                    primeiro = false;
                    Escreve(sb, item);
                }
                sb.Append(']');
                return;
            }

            // objeto anonimo / POCO: propriedades publicas
            sb.Append('{');
            bool p0 = true;
            foreach (var p in v.GetType().GetProperties())
            {
                if (!p.CanRead || p.GetIndexParameters().Length > 0) continue;
                if (!p0) sb.Append(',');
                p0 = false;
                Texto(sb, p.Name);
                sb.Append(':');
                Escreve(sb, p.GetValue(v));
            }
            sb.Append('}');
        }

        private static void Texto(StringBuilder sb, string s)
        {
            sb.Append('"');
            foreach (char c in s ?? "")
            {
                switch (c)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (c < 0x20 || c > 0x7E) sb.Append("\\u" + ((int)c).ToString("x4"));
                        else sb.Append(c);
                        break;
                }
            }
            sb.Append('"');
        }

        // ---------- ler ----------

        internal static Dictionary<string, object> LerObjeto(string texto)
        {
            var p = new Leitor(texto ?? "");
            object v = p.Valor();
            return v as Dictionary<string, object> ?? new Dictionary<string, object>();
        }

        private sealed class Leitor
        {
            private readonly string _s;
            private int _i;

            internal Leitor(string s) { _s = s; }

            internal object Valor()
            {
                Pula();
                if (_i >= _s.Length) return null;
                char c = _s[_i];
                if (c == '{') return Objeto();
                if (c == '[') return Lista();
                if (c == '"') return Cadeia();
                if (c == 't') { _i += 4; return true; }
                if (c == 'f') { _i += 5; return false; }
                if (c == 'n') { _i += 4; return null; }
                return Numero();
            }

            private Dictionary<string, object> Objeto()
            {
                var d = new Dictionary<string, object>();
                _i++; // {
                Pula();
                if (_i < _s.Length && _s[_i] == '}') { _i++; return d; }
                while (_i < _s.Length)
                {
                    Pula();
                    string chave = Cadeia();
                    Pula();
                    if (_i < _s.Length && _s[_i] == ':') _i++;
                    d[chave] = Valor();
                    Pula();
                    if (_i >= _s.Length) break;
                    if (_s[_i] == ',') { _i++; continue; }
                    if (_s[_i] == '}') { _i++; break; }
                    _i++; // lixo: segue
                }
                return d;
            }

            private List<object> Lista()
            {
                var l = new List<object>();
                _i++; // [
                Pula();
                if (_i < _s.Length && _s[_i] == ']') { _i++; return l; }
                while (_i < _s.Length)
                {
                    l.Add(Valor());
                    Pula();
                    if (_i >= _s.Length) break;
                    if (_s[_i] == ',') { _i++; continue; }
                    if (_s[_i] == ']') { _i++; break; }
                    _i++;
                }
                return l;
            }

            private string Cadeia()
            {
                var sb = new StringBuilder();
                _i++; // abre aspas
                while (_i < _s.Length)
                {
                    char c = _s[_i++];
                    if (c == '"') break;
                    if (c != '\\') { sb.Append(c); continue; }
                    if (_i >= _s.Length) break;
                    char e = _s[_i++];
                    switch (e)
                    {
                        case 'n': sb.Append('\n'); break;
                        case 'r': sb.Append('\r'); break;
                        case 't': sb.Append('\t'); break;
                        case 'b': sb.Append('\b'); break;
                        case 'f': sb.Append('\f'); break;
                        case 'u':
                            if (_i + 4 <= _s.Length)
                            {
                                sb.Append((char)Convert.ToInt32(_s.Substring(_i, 4), 16));
                                _i += 4;
                            }
                            break;
                        default: sb.Append(e); break;
                    }
                }
                return sb.ToString();
            }

            private object Numero()
            {
                int ini = _i;
                while (_i < _s.Length && "+-0123456789.eE".IndexOf(_s[_i]) >= 0) _i++;
                var t = _s.Substring(ini, _i - ini);
                double d;
                return double.TryParse(t, NumberStyles.Any, CultureInfo.InvariantCulture, out d) ? d : (object)0.0;
            }

            private void Pula()
            {
                while (_i < _s.Length && char.IsWhiteSpace(_s[_i])) _i++;
            }
        }
    }
}
