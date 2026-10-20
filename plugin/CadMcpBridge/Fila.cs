using System.Collections.Concurrent;
using System.Threading;
using AcApp = Autodesk.AutoCAD.ApplicationServices.Core.Application;

namespace CadMcpBridge
{
    /// <summary>
    /// Marshalling para a thread principal do AutoCAD SEM travar o AutoCAD.
    ///
    /// Por que existe: `DocumentManager.ExecuteInApplicationContext` era usado aqui
    /// e travava o thread principal de forma irreversivel quando chamado da thread
    /// da ponte (o primeiro `ping` congelava o AutoCAD: o COM parava de responder
    /// com RPC_E_CALL_REJECTED e so um kill resolvia).
    ///
    /// Agora o trabalho entra numa fila e e' executado no evento `Application.Idle`,
    /// que ja' roda na thread principal. A thread da ponte espera com PRAZO: se o
    /// AutoCAD nao ficar ocioso, devolvemos TimeoutException em vez de pendurar
    /// todo mundo. Timeout nunca deixa thread principal presa.
    /// </summary>
    internal static class Fila
    {
        internal sealed class Item
        {
            internal readonly Func<object> Trabalho;
            internal readonly ManualResetEventSlim Pronto = new ManualResetEventSlim(false);
            internal object Resultado;
            internal System.Exception Erro;
            internal volatile bool Cancelado;

            internal Item(Func<object> trabalho) { Trabalho = trabalho; }
        }

        private static readonly ConcurrentQueue<Item> _itens = new ConcurrentQueue<Item>();
        private static int _threadPrincipal = -1;
        private static int _inscrito;

        /// <summary>Chamar de Initialize(), que roda na thread principal.</summary>
        internal static void Iniciar()
        {
            _threadPrincipal = Thread.CurrentThread.ManagedThreadId;
            if (Interlocked.Exchange(ref _inscrito, 1) == 0)
            {
                AcApp.Idle += AoOcioso;
                Servidor.Log("fila: inscrita no Application.Idle (thread principal " + _threadPrincipal + ")");
            }
        }

        private static void AoOcioso(object sender, System.EventArgs e) => Drenar();

        /// <summary>Consome a fila na thread principal. Idempotente.</summary>
        internal static void Drenar()
        {
            Item item;
            while (_itens.TryDequeue(out item))
            {
                if (item.Cancelado)
                {
                    item.Pronto.Set();
                    continue;
                }
                try
                {
                    item.Resultado = item.Trabalho();
                }
                catch (System.Exception ex)
                {
                    item.Erro = ex;
                }
                finally
                {
                    item.Pronto.Set();
                }
            }
        }

        internal static T NoContexto<T>(Func<T> trabalho, int timeoutMs)
        {
            // Ja' estamos na thread principal (ex.: chamado de dentro de um comando):
            // executar direto evita esperar por um Idle que nunca viria.
            if (Thread.CurrentThread.ManagedThreadId == _threadPrincipal)
                return trabalho();

            var item = new Item(() => trabalho());
            _itens.Enqueue(item);
            if (!item.Pronto.Wait(timeoutMs))
            {
                item.Cancelado = true;
                throw new System.TimeoutException(
                    "AutoCAD ocupado: o thread principal nao ficou ocioso em " + timeoutMs + " ms");
            }
            if (item.Erro != null) throw item.Erro;
            return (T)item.Resultado;
        }
    }
}
