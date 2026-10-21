using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Text.Json;

// Le a metadata (ECMA-335) das DLLs gerenciadas do AutoCAD sem carrega-las.
// Carregar nao daria: sao net8.0 e dependem do runtime do acad.exe.
//
// Uso: MapaDotnet <saida.json> <dll> [dll...]

if (args.Length < 2)
{
    Console.Error.WriteLine("uso: MapaDotnet <saida.json> <dll> [dll...]");
    return 2;
}

var porTipo = new List<Dictionary<string, object>>();
var porAssembly = new Dictionary<string, int>();

foreach (var dll in args.Skip(1))
{
    var nomeAssembly = Path.GetFileNameWithoutExtension(dll);
    using var fs = File.OpenRead(dll);
    using var pe = new PEReader(fs);
    if (!pe.HasMetadata) { Console.Error.WriteLine($"{nomeAssembly}: sem metadata"); continue; }
    var mr = pe.GetMetadataReader();
    int contados = 0;

    foreach (var th in mr.TypeDefinitions)
    {
        var td = mr.GetTypeDefinition(th);
        var vis = td.Attributes & TypeAttributes.VisibilityMask;
        if (vis != TypeAttributes.Public && vis != TypeAttributes.NestedPublic) continue;

        var ns = mr.GetString(td.Namespace);
        var nome = mr.GetString(td.Name);
        if (string.IsNullOrEmpty(nome) || nome.StartsWith("<")) continue;

        var baseNome = "";
        if (!td.BaseType.IsNil)
        {
            baseNome = td.BaseType.Kind switch
            {
                HandleKind.TypeReference => NomeDoTipo(mr, (TypeReferenceHandle)td.BaseType),
                HandleKind.TypeDefinition => NomeDoTipoDef(mr, (TypeDefinitionHandle)td.BaseType),
                _ => "",
            };
        }

        var metodos = new List<string>();
        foreach (var mh in td.GetMethods())
        {
            var md = mr.GetMethodDefinition(mh);
            var mvis = md.Attributes & MethodAttributes.MemberAccessMask;
            if (mvis != MethodAttributes.Public) continue;
            var mnome = mr.GetString(md.Name);
            if (string.IsNullOrEmpty(mnome) || mnome.StartsWith("<") || mnome.StartsWith("get_")
                || mnome.StartsWith("set_") || mnome.StartsWith("add_") || mnome.StartsWith("remove_"))
                continue;
            int n = 0;
            foreach (var _ in md.GetParameters()) n++;
            metodos.Add($"{mnome}/{n}");
        }

        var props = new List<string>();
        foreach (var ph in td.GetProperties())
        {
            var pd = mr.GetPropertyDefinition(ph);
            var pnome = mr.GetString(pd.Name);
            if (!string.IsNullOrEmpty(pnome)) props.Add(pnome);
        }

        if (metodos.Count == 0 && props.Count == 0) continue;

        porTipo.Add(new Dictionary<string, object>
        {
            ["a"] = nomeAssembly,
            ["ns"] = ns,
            ["t"] = nome,
            ["b"] = baseNome,
            ["m"] = metodos,
            ["p"] = props,
        });
        contados++;
    }
    porAssembly[nomeAssembly] = contados;
    Console.Error.WriteLine($"{nomeAssembly}: {contados} tipos");
}

var saida = new Dictionary<string, object>
{
    ["gerado_em"] = DateTime.Now.ToString("yyyy-MM-dd"),
    ["fonte"] = "metadata das DLLs gerenciadas do AutoCAD (System.Reflection.Metadata)",
    ["assemblies"] = porAssembly,
    ["tipos"] = porTipo,
};

var json = JsonSerializer.Serialize(saida, new JsonSerializerOptions { WriteIndented = false });
File.WriteAllText(args[0], json);
Console.Error.WriteLine($"{porTipo.Count} tipos -> {args[0]}");
return 0;

static string NomeDoTipo(MetadataReader mr, TypeReferenceHandle h)
{
    var tr = mr.GetTypeReference(h);
    var ns = mr.GetString(tr.Namespace);
    var n = mr.GetString(tr.Name);
    return string.IsNullOrEmpty(ns) ? n : ns + "." + n;
}

static string NomeDoTipoDef(MetadataReader mr, TypeDefinitionHandle h)
{
    var td = mr.GetTypeDefinition(h);
    var ns = mr.GetString(td.Namespace);
    var n = mr.GetString(td.Name);
    return string.IsNullOrEmpty(ns) ? n : ns + "." + n;
}
