using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.Runtime;
using CadMcpBridge;

[assembly: ExtensionApplication(typeof(Inicio))]
[assembly: CommandClass(typeof(Comandos))]

namespace CadMcpBridge
{
    /// <summary>
    /// Entrada do plugin. Carregado pelo Autoloader (.bundle) junto com o AutoCAD,
    /// ou por NETLOAD manual. Nao desenha nada aqui: so sobe a ponte.
    /// </summary>
    public class Inicio : IExtensionApplication
    {
        public void Initialize()
        {
            try
            {
                Servidor.Iniciar();
            }
            catch (System.Exception ex)
            {
                // nunca derrubar o AutoCAD por causa da ponte, mas tambem nunca
                // falhar em silencio: sem esta linha um erro de carga vira um
                // "nao aconteceu nada" impossivel de diagnosticar.
                try { Servidor.Log("Initialize falhou: " + ex); } catch { }
                System.Diagnostics.Debug.WriteLine("CadMcpBridge: " + ex);
            }
        }

        public void Terminate()
        {
            Servidor.Parar();
        }
    }

    public static class Comandos
    {
        [CommandMethod("MPCBRIDGE", CommandFlags.Session)]
        public static void Status()
        {
            var doc = Application.DocumentManager.MdiActiveDocument;
            var ed = doc?.Editor;
            ed?.WriteMessage("\nCadMcpBridge: " + Servidor.Estado() + "\n");
        }
    }
}
