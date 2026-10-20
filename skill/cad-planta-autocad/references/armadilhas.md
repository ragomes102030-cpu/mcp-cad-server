# Armadilhas do AutoCAD via COM/AutoLISP — sintoma, causa, correção

Todas foram encontradas na prática, com o `mcp-cad-server`. Nenhuma dá mensagem de erro
útil. Leia isto **antes** de mexer no motor ou de estranhar um desenho "quase certo".

---

## 1. `entmake`/`entget` usam RADIANOS nos grupos de ângulo (50/51)

**Sintoma.** A entidade existe, com centro, raio, camada e handle corretos — mas girada.
Porta de 90° nasce com **116,620° de abertura**. Nenhuma exceção, nenhum erro. O contador
de erros diz "0 erros".

**Causa.** No AutoLISP, uma entity list passada para `entmake`/`entmakex` espera o grupo
50/51 em radianos, e `entget` devolve radianos. No **arquivo DXF** os mesmos grupos são
graus — a conversão acontece nas costas.

**Assinatura do bug:** `grau_gravado = degrees(grau_pedido)`.
Porque o número foi lido como radiano: `90 rad mod 2π = 2,0354 rad = 116,62°`.

```
90  -> 116,620156177409      (= 90 rad em graus, mod 360)
0   -> 0
30  -> 278,8733853924698     (= 30 rad mod 2π, em graus)
120 -> 35,49354156987917
```

**Correção.** Converta sempre. Em LISP, `(angtof "90")` converte usando a unidade
corrente (`AUNITS=0` = graus decimais) e devolve radianos. Em Python, `math.radians(graus)`.

```lisp
(entmakex '(... (cons 50 90)       (cons 51 180)))         ; ERRADO
(entmakex '(... (cons 50 (angtof "90")) (cons 51 (angtof "180"))))  ; CERTO
```

Vale para ARC (50/51), TEXT/MTEXT (50 = rotação), INSERT (50), HATCH (52).
**Não vale** para entidades criadas por **comando** (`DIMLINEAR`, `HATCH`, `LINE`, `ARC`):
esses recebem graus normalmente.

**Onde está a checagem:** `scripts/conferir.py` mede a abertura de todo arco e grita
se não for 90°,00. `scripts/render_planta.py` faz o mesmo no fim do render.

---

## 2. Contagem de entidades e `erros=0` não provam nada

**Sintoma.** Você confere "112 entidades, 0 erros" e o desenho está errado (caso 1).
Ou: a porta não está no lugar, o texto invadiu a parede, a legenda estourou a folha.

**Causa.** Contar existência é fácil; medir **propriedade** é o que valida.
"Existe uma entidade ARC" não diz que ela abre 90°.

**Correção.** Verifique propriedades específicas do que você desenhou:
abertura de arco, `INSUNITS`, área das polilinhas fechadas, extensão (extents) em metros,
textos esperados presentes, folha/tinta do PDF.
Use `scripts/conferir.py` + `scripts/validar_pdf.py`, e **compare com o que você projetou**,
não só com a ausência de erro.

---

## 3. `SendCommand` trata ESPAÇO como ENTER

**Sintoma.** Comando cortado no meio; ou (em caminhos com espaço) a parte depois do
espaço executada como um segundo comando. Já me fez concluir, errado, que existia
um "limite de 255 caracteres".

**Causa.** `SendCommand` injeta texto no prompt de comando do AutoCAD.

**Correção.** Todo caminho de trabalho **sem espaço**: `C:\temp\mcp_cad_com`
(`MCP_CAD_TEMP`). Passe listas longas de LISP como **uma linha** (o `_uma_linha` do
`com_backend.py` faz isso, preservando espaços **dentro** de literais de string).

---

## 4. `SendCommand` precisa do `\n` no fim

**Sintoma.** O primeiro comando funciona e o seguinte estoura; depois o AutoCAD
recusa todas as chamadas COM.

**Causa.** Sem o ENTER final, o AutoCAD fica esperando o fim do comando e bloqueia.

**Correção.** Sempre acrescente `\n` (o `_send` do `com_backend.py` já garante).

---

## 5. Nunca `(load "arquivo.lsp")` — mata o COM

**Sintoma.** Todas as chamadas COM passam a devolver `RPC_E_CALL_REJECTED`
(0x80010001 / -2147418111). Nada mais funciona.

**Causa.** Com `SECURELOAD` ligado, o AutoCAD abre um **diálogo modal**
*"Security - Unsigned Executable File"*. Diálogo modal bloqueia toda chamada COM.

**Correção.** Envie o LISP **inline** dentro de `SendCommand`, nunca por `load`.
Se travar: feche os diálogos (`#32770`) e mande ESC na janela do AutoCAD
(`win32_bridge.find_autocad_window()` + `enviar_esc`). Retry com backoff é obrigatório
em `RPC_E_CALL_REJECTED` (-2147418111, -2147417846, -2147417847).

---

## 6. O DXF sai "velho": `accoreconsole` lê o DISCO

**Sintoma.** Você cria entidades, exporta o DXF e elas não estão lá. Parece bug de
exportação.

**Causa.** A exportação DXF roda no `accoreconsole.exe`, que abre o **arquivo salvo**,
não o desenho em memória da sua sessão COM.

**Correção.** **Salve o DWG antes de exportar o DXF.** Ordem obrigatória:
`drawing_save` → `drawing_save_as_dxf`.

---

## 7. "Error saving the document" ao salvar em cima de um DWG existente/aberto

**Sintoma.** `drawing_save` devolve "Error saving the document".

**Causa.** O arquivo de destino já existe, ou **está aberto** na sessão do AutoCAD
(um documento anterior não foi fechado — `drawing_create` não fecha o que estava aberto).

**Correção.** Apague o destino antes de salvar e, se ainda assim falhar, tente outro
nome (`_2`, `_3`). O `scripts/render_planta.py` já faz esse fallback e propaga o nome
real para o DXF/PDF.

---

## 8. `WBLOCK` sempre abre diálogo — use `-WBLOCK` (ou o accoreconsole)

**Sintoma.** Travamento, ou `RPC_E_CALL_REJECTED`, ao tentar gravar um bloco em arquivo.

**Causa.** `WBLOCK` ignora `FILEDIA=0` e abre o diálogo.

**Correção.** `-WBLOCK` (com o hífen) ou, melhor, deixe o `accoreconsole` fazer a
conversão de arquivo.

---

## 9. `SaveAs` renomeia o desenho do usuário — nunca use para exportar DXF

**Sintoma.** Depois do "export", o desenho aberto do usuário mudou de nome.

**Causa.** `SaveAs` no `ActiveDocument` renomeia a sessão, não faz uma cópia.

**Correção.** Exporte via `accoreconsole` (headless). Nunca `SaveAs` para DXF.

---

## 10. Texto do AutoCAD é largo: ~0,9 × altura por caractere

**Sintoma.** Texto vaza da parede / do ambiente. Ou: a folha fica com o desenho miúdo
e muito espaço em branco, porque o plot usa *Extents* e a legenda esticou o
enquadramento inteiro (uma linha de 100 caracteres a 0,22 m ocupa **~20 m** de papel).

**Causa.** No `txt.shx`, caixa-alta avança perto de 0,9 × altura (não os 0,6 que a
gente assume de cabeça).

**Correção.** Estime `n_chars × altura × 0,9` antes de escrever. Quebre o selo em
linhas de ~70 caracteres e mantenha a largura total menor que a do terreno.

---

## 11. Ao "olhar" o desenho por rasterização, cuidado com aliasing

**Sintoma.** A conferência em ASCII mostra a planta sem as paredes externas. Parece
desastre; era o verificador.

**Causa.** Parede de 0,15 m some quando você amostra só o **centro** de células de 0,2 m.

**Correção.** Sub-amostragem (5×5 por célula) — é o que `scripts/conferir.py --mapa` faz.
**Regra geral: quando o verificador acusa problema, desconfie primeiro dele.**

---

## 12. `INSUNITS` manda no significado dos números

**Sintoma.** O desenho "está certo" mas o AutoCAD mostra tudo em milímetros/polegadas.

**Causa.** O desenho não estava em metros.

**Correção.** `drawing_setup(unidades=6)` (`INSUNITS=6` = metros) e confira no DXF:
`scripts/conferir.py` mostra o `INSUNITS` e marca OK/CONFERIR.

---

## 13. `dimension_linear` sai em escala de papel (DIMTXT 2,5) — não dá planta 1:50

**Sintoma.** A cota existe, com as medidas certas, mas o número tem **2,5 m de altura**
num desenho de 12 m: atravessa o desenho inteiro. `dim_aligned` idem.

**Causa.** A `AcDbRotatedDimension` usa o estilo corrente do documento
(`DIMTXT=2,5`, `DIMSCALE=1`). O `drawing_setup` do `com_backend.py` já ajustava
`DIMSCALE`/`TEXTSIZE`, mas **não estava exposto** em `tools.py`.

**Correção (17/10/2026).** A ferramenta agora existe: `drawing_setup(unidades=6,
escala_cota=0.1)` **depois** de `drawing_new`. Ela põe `DIMSCALE=0,1` (texto de cota
2,5 × 0,1 = **0,25 m**), `DIMDEC=2` (sai "5,00", não "5"), `DIMTAD=1` (texto acima da
linha), `LUPREC=2` e `INSUNITS=6`. Testado no AutoCAD 2025: dimensão de 5,00 m com texto
de 0,250 m e vírgula decimal.

**Reforço (19/10/2026).** `drawing_setup` passou a **cravar** também `DIMTXT=2,5`,
`DIMGAP=0,5`, `DIMTIH=0`, `DIMTOH=0`, `DIMLUNIT=2` e `DIMBLK="."`.
Motivo: essas variáveis herdavam o seed do template, e duas rodadas do mesmo prompt saíam
com **extensões diferentes só por causa do texto da cota** ("11" × "11,00" muda a largura do
`DIMENSION` e portanto `EXTMIN`/`EXTMAX`; no comparativo 24,49 × 24,5542 a diferença de
6,4 cm era toda do texto da cota — as 195 entidades não-DIMENSION eram idênticas). Medido no
DXF, na própria entidade (`get_acad_dstyle`): `dimasz=1.0`, `dimexe=0.6`, `dimexo=0.4`,
`dimgap=0.5`, `dimscale=0.1`, `dimzin=0`, `MTEXT` com altura 0,25 m; cota de 11 m criada sem
erro e `quantitativo` ok. O estilo `ISO-25` continua com os valores de fábrica — são
**overrides por entidade**, e é isso que importa (ver a armadilha do `GetVariable`).

**LTSCALE — o valor certo depende do padrão, não só do número (medido 19/10).**
`drawing_setup(..., ltscale=0.2)` agora é o default. Com o `DASHED` do **acad.lin**
(`0,5 / -0,25`) a 1:50:

| LTSCALE | ciclo no papel | traços no círculo r=0,40 m | leitura |
|---|---|---|---|
| 0,05 | 0,75 mm | ~67 | parece contínuo |
| **0,2** | **3,0 mm** | **~17** | **tracejado legível** |
| 1,0 | 15 mm | ~3 | grosseiro, quase traço cheio |

Como o padrão do `DASHED` pode vir do **acadiso.lin** (`12,7 / -6,35`, 25× maior), o mesmo
LTSCALE dá resultado 25× diferente — confira o código 49 do LTYPE no DXF antes de julgar.
O valor antigo "12,7 m de traço" que circulou era do acadiso; com acad.lin o 1,0 dava 0,5 m
(10 mm no papel a 1:50).

**`GetVariable` prova o estilo corrente, não a cota criada.** Para saber o que a `DIMENSION`
realmente usa, leia a **entidade**: no DXF, os overrides aparecem como códigos 40/41/42/44/
147/271/78 na própria `DIMENSION` (no ezdxf, `dim.get_acad_dstyle(doc.dimstyles.get(
dim.dxf.dimstyle))`). Medido com o setup novo: a entidade carrega `dimscale=0.1, dimasz=1.0,
dimexo=0.4, dimexe=0.6, dimgap=0.5, dimzin=0`, enquanto o estilo `ISO-25` continua em
2,5 / 0,625.

**O override é PARCIAL** — regra: `efetivo(k) = override(k) se existir, senão estilo(k)`.
No DXF do reteste (anterior ao pinning do DIMGAP), os overrides eram só
`{dimscale, dimasz, dimexo, dimexe, dimzin}`; o gap efetivo vinha do estilo (0,625 × 0,1 =
0,0625), não de 0,5. Ler só o override ("não aplicou") erra tanto quanto ler só o estilo
("aplicou"). O `$DIM*` do header é a variável de sistema no momento de salvar — não fala da
entidade.

**Seta:** `DIMBLK "."` → `SOLID` de 3 pontos dentro do bloco `*D<N>`; `DIMBLK
_CLOSEDFILLED` (a seta padrão **nomeada**) → `INSERT` desse bloco. Contar tipos no bloco
mede a *forma* do DIMBLK, não se ele foi aplicado.


**Plano B (ainda válido).** Sem `drawing_setup`, cota à mão: linha de extensão + linha de
cota + tick oblíquo (45°, 0,15) + `entity_create_text` 0,25 na camada COTA. Texto de cota
**vertical** (rotação 90) cresce para −x a partir do ponto de inserção: desloque
`0,06 + h` para o lado da linha, senão o número cai **em cima** da linha.

**Medida:** 16 cotas manuais = 96 entidades na camada COTA (planta 12 × 10).

---

## 14. Largura de texto: 0,9323 × altura por caractere — e depende de COMO o desenho nasceu

**Sintoma.** Título de 27 caracteres a h = 0,40 "centralizado em x = 6,00" apareceu
centrado em 5,43; depois em 6,19. Rótulos vazando da parede.

**Causa.** Duas coisas. (a) A fonte avança **0,9323 × h** por caractere, não 0,68/0,90
estimados de cabeça. (b) A mesma fonte mediu **0,791 × h** num documento criado por
`Documents.Add()` via COM, e **0,9323** num criado por `drawing_new`. O estilo de texto
herdado muda com o método de criação.

**Correção.** Meça **nesta sessão, neste documento**: escreva um texto de 20–30
caracteres, exporte o DXF e divida a largura da caixa por `h × n`. Centralize com o
número medido; se o desenho for recriado, meça de novo.

**Onde está a checagem:** `conferir2.py` (caixa de tinta, rotação 90 tratada) e a
auto-redução do nome de ambiente até caber na largura útil − 0,24.

---

## 15. Vão não é só "apagar o trecho": sem ombreira a parede fica aberta

**Sintoma.** Na imagem, cada porta/janela deixa dois tocos de parede com a espessura
**aberta** nas pontas. O contador de erros não vê nada. O verificador achou **66 pontas
soltas** numa planta de 8 portas e 7 janelas.

**Causa.** A parede é modelada por duas faces (t/2 para cada lado). Subtrair o vão das
duas faces deixa 4 pontas soltas por vão, e nada fecha a espessura.

**Correção.** Em cada ponta de vão, desenhe uma **ombreira**: segmento perpendicular ao
eixo, de −t/2 a +t/2. 15 vãos → 30 ombreiras → 0 pontas soltas.

**Variante irmã:** parede externa com face externa e interna invertidas no trecho → fresta
de 0,15 m no canto. Confira canto por canto: externa de −0,075 a L+0,075, interna de
+0,075 a L−0,075.

---

## 16. Três ferramentas devolvem `ok` mentindo (caminho, arquivo velho, imagem vazia)

| ferramenta | o que promete | o que faz de fato |
|---|---|---|
| `drawing_export_pdf` | plota no caminho pedido | **corrigido em 17/10**: antes devolvia `ok` e deixava o PDF **antigo** (23.304 bytes) quando o arquivo estava aberto no Acrobat. Agora apaga o destino antes, exige `mtime` novo ou exclusão bem-sucedida e, se não regravar, devolve `ok=false` com "PDF nao foi regravado" |
| `view_screenshot` | grava em `path` | grava sempre em `C:\temp\mcp_cad_com\autocad_screenshot.png`, e saiu **160 × 28 px** — inútil para inspeção |
| `drawing_new` | cria em `path` | **corrigido em 17/10**: antes, se a pasta não existia criava `Drawing2` e ignorava o caminho, e se o arquivo já estava aberto criava `Drawing5` com o `save` falhando. Agora procura o documento **pelo caminho** (reaproveita se já aberto), cria a pasta, e devolve `ok=false` com o erro real se o `SaveAs` falhar |

**Regra.** Depois de qualquer `ok`, confira o **artefato**: `mtime`, tamanho, e no DXF o
conteúdo. `ok` é o retorno da chamada, não a prova de que o arquivo mudou.

---

## 17. Existem DUAS cópias do projeto — a de referência e a que o servidor executa

**Sintoma.** A ferramenta nova "não existe" para o agente, mesmo com o código editado e
o teste unitário passando.

**Causa.** O `mcp_servers.command` aponta para `C:\Users\Correta Engenharia\mcp-cad-server`
(`python src\cad_mcp\server.py`); a pasta `Desktop\Mapeamento AutoCad\codigo` é a **cópia
de referência** (de onde sai a entrega). Editar só uma delas não muda nada no servidor.

**Correção.** A referência manda: editar **primeiro** em `Desktop\Mapeamento AutoCad\codigo\src`,
sincronizar para a cópia que o comando aponta e **reiniciar a conversa/servidor** — a lista
de ferramentas é negociada no handshake, não recarrega sozinha.

**Atalho definitivo (testado).** O caminho da referência funciona como servidor, mesmo com
espaço no nome: `command` = Python do venv, `args` =
`["-m", "cad_mcp.server"]` com `cwd` na referência, ou `["C:\Users\...\Desktop\Mapeamento
AutoCad\codigo\src\cad_mcp\server.py"]`. Respondeu 45 ferramentas no handshake. Aí só existe
uma cópia para manter.

---

## 18. Sem `erase` a correção custa o desenho inteiro (a lição mais cara)

**Sintoma.** Um rótulo sobreposto → 6 reexecuções completas do gerador (251 entidades
cada) para corrigir 5 textos, 2 cantos e 1 janela.

**Causa.** O MCP tinha 36 ferramentas e **nenhuma de apagar/mover**, embora o COM tenha
`Entity.Delete` desde sempre. A lacuna não era do AutoCAD: era da superfície exposta.

**Correção (16/10/2026).** `entity_erase(handle)`, `entity_erase_filter(layer|tipo|texto,
confirmar)` com pré-visualização e recusa sem filtro, `entity_move(handle, dx, dy)` e
`entity_list(layer, tipo)` corrigido (devolvia 1 item por camada por filtro LISP mal
formado). O custo de corrigir agora é proporcional ao que está errado, não ao desenho.

**Testado (17/10/2026), planta em L:** T1–T10 passaram. `entity_move` **não travou** e o
deslocamento voltou exato (0,400000 m medido no DXF, ida e volta). `entity_erase_filter`
com prévia não alterou o desenho; com `confirmar=True` apagou exatamente o contado
(1 texto, 14 do carimbo, 3 do vão J11). Recontar com `entity_list` depois de apagar é o
que prova — não o `ok`.

---

## 19. DXF sai em milímetros (INSUNITS=4) mesmo com o desenho em metros

**Sintoma.** Desenho perfeito em metros, mas o `$INSUNITS` do DXF é **4 (mm)**. Quem
importar (Revit, SketchUp, outro CAD) lê 14.000 mm em vez de 14 m. O agente só descobre
se abrir o header no `ezdxf` — a imagem e o AutoCAD não reclamam.

**Causa.** `drawing_new` não define unidade, e não havia ferramenta de variável de sistema.
`INSUNITS=0` (sem unidade) e `4` (mm) são o default de fábrica.

**Correção (17/10/2026).** `drawing_setup(unidades=6)` **depois** de `drawing_new`.
Verificado no DXF: `$INSUNITS = 6` (metros), `$LUPREC = 2`, `$DIMSCALE = 0,1`.

**Regra.** Unidade não é cosmética: é o que separa 14 m de 14 km no arquivo de troca.

---

## 20. Parênteses fechados não querem dizer LISP válido — e o erro trava o AutoCAD

**Sintoma.** `entity_offset` nunca voltava: 30 s de timeout, nenhum diálogo, nenhuma linha
de erro. O AutoCAD ficava com **100% de CPU** e o COM passou a recusar chamadas
(`RPC_E_CALL_REJECTED`). Fechar o desenho era impossível.

**Causa.** Faltava um `)` no lugar certo e sobrava outro no fim:

```lisp
(if __h (cdr (assoc 5 (entget __h))) -3)   ; 3 argumentos: ok
...
(if (< __L 1e-9) -2 (progn ...)) (if __h ...) -3   ; virou (if teste a b EXTRA)
```

O `progn` fechava cedo e o `(if __h ...)` caía como **4º argumento** do `if` de fora.
A contagem total de parênteses continuava **zero** — por isso o checador de balanço não
pegou. O `SendCommand` recebeu `(if ... 4 args)` → erro de sintaxe, linha de comando presa.

**Diagnóstico.** O mesmo programa, mandado ao `accoreconsole` (batch, sem GUI), mostrou
`; error: syntax error` na hora. **Sempre que um LISP do backend "travar", reproduza em
`accoreconsole`** — é isolado e não arrisca o AutoCAD do usuário.

**Correção.** `codigo/tools/checa_lisp.py`: monta a **árvore** (não só conta parênteses) e
valida aridade de `if` (2 ou 3), `setq` (par), `progn` (não vazio). Roda sem AutoCAD.

**Destravar.** `PostMessage`/`keybd_event` sem foco **não** funcionaram. O que funcionou:
`AttachThreadInput` + `SetForegroundWindow` + `SendInput` com `VK_ESCAPE` (6×).

---

## 21. `handent` devolve ENAME; `vla-*` exige VLA-OBJECT

**Sintoma.** `bad argument type: VLA-OBJECT <Entity name>` em `vla-move`, `vla-copy`,
`vla-rotate`, `vla-mirror`.

**Causa.** `(handent "80")` devolve o **ename**, não o objeto ActiveX.

**Correção.** `(vlax-ename->vla-object (handent h))`. O `entity_offset` (que usa `entget`,
não `vla-*`) é o único que aceita o ename direto.

---

## 22. Todo LISP roda no documento ATIVO, não no documento guardado

**Sintoma.** `entity_rotate` devolveu `0` (não achou a entidade) e `entity_count` devolveu
298 — o número da *outra* planta. Metade do teste rodou num desenho e metade no outro,
sem erro nenhum.

**Causa.** `handent`, `ssget` e `entmakex` operam no **documento ativo** do AutoCAD. Se o
usuário (ou uma chamada COM) traz outra janela para a frente, o `_doc` guardado pelo backend
deixa de ser o alvo e o handle "some". `ssget "_X"` chega a listar as entidades do desenho
errado.

**Correção.** Em `ComBackend._send()`: comparar `ActiveDocument.Name` com o documento alvo e
chamar `doc.Activate` antes de cada `SendCommand`. Foi o que fez os cinco tools novos
passarem depois de 8 falhas seguidas.

---

## 23. `outro is doc` nunca é `True` com pywin32

**Sintoma.** `drawing_save` recusava salvar: *"'...dwg' já está aberto no AutoCAD como outro
desenho"* — sendo o mesmo desenho.

**Causa.** Cada acesso COM do pywin32 cria um **wrapper novo** para o mesmo objeto. Comparar
com `is` compara wrappers, não documentos.

**Correção.** Comparar `FullName` normalizado (`os.path.normcase(os.path.abspath(...))`).
Vale para qualquer comparação de objetos COM.

---

## 24. AutoCAD na tela inicial → `file_ipc` → TODA chamada estoura timeout

**Sintoma.** O servidor sobe, `drawing_new` "funciona", `drawing_setup` "funciona", mas
`layer_create` demora ~10 s e volta `Timeout waiting for result`; o agente conclui que o
backend é `file_ipc`. `layer_list` volta vazio. Nada é desenhado.

**Causa.** Com o AutoCAD aberto na tela inicial (nenhum desenho), `GetActiveObject
("AutoCAD.Application")` funciona, mas `ActiveDocument` levanta erro. No `mode=auto` isso
fazia o `BackendManager` cair na **ponte LISP por arquivo**, que só funciona com o
dispatcher carregado. Sem dispatcher, cada comando vira um arquivo que ninguém lê.

**Correção (19/10/2026).**
1. `ComBackend._conectar`: se não há `ActiveDocument`, cria um (`Documents.Add`, 3 tentativas).
2. `BackendManager`: no `auto`, AutoCAD aberto + COM falhando agora devolve **erro explícito**
   (com o motivo do COM) em vez de escolher `file_ipc` calado. `file_ipc` só entra se
   `CAD_MCP_BACKEND=file_ipc` ou `autocad`.

**Regra.** Antes de subir o servidor, deixe **um desenho aberto** no AutoCAD.

---

## 25. Um AutoCAD, dois agentes = RPC rejeitado e CAD caindo

**Sintoma.** `(-2147418111, 'Call was rejected by callee.')` em sequência; depois o
`drawing_plot_pdf` derruba o AutoCAD; o DWG "desaparece" do disco; sobram `.dwl`, `.dwl2`
e `.ac$`.

**Causa.** Duas conversas mandando `SendCommand` no mesmo AutoCAD ao mesmo tempo. Não é
bug do backend — é concorrência no mesmo processo.

**Regra.** **Uma conversa por vez** usando o AutoCAD. Para rodar duas em paralelo, abra
outra instância (`acad /n`) e aponte o backend para ela.

---

## 26. `drawing_plot_pdf` / `drawing_export_pdf` ignoram a escala (A4 "fit")

**Medido no teste de 19/10.** Página **A4 retrato**, 1.669 operações vetoriais, largura útil
de 197 mm para 22 m de prancha → escala efetiva **1:111** (o pedido era 1:50). Os textos
saem **vetorizados** (não são texto selecionável no PDF).

**Pendência.** Aceitar `folha` (A1/A3) e `escala` nos dois tools. Hoje é sempre "fit to A4".

**Resolvido em 19/10** — ver armadilha **32** (`folha`/`escala` implementados).

**Nota.** O plot em si funciona: 3,5 s, `ok=true`, `retorno=true`, 41.670 bytes — desde que
haja **um** agente mexendo no CAD.

---

## 27. Servidor com 45 tools, conversa abrindo com 0

**Sintoma.** `diagnose conversations get` mostra `mcp_server_ids: []`; o agente não tem
nenhuma `entity_*` e responde "não tenho ferramentas CAD".

**Causa.** O assistant `Aion CLI` (`bare:632f31d2`) estava com
`defaults.mcps = {mode: "auto"}` e o auto **não injetou** o servidor nas conversas criadas
pelo CLI.

**Correção.** `config assistants update` com
`defaults.mcps = {mode: "fixed", value: ["mcp_01a1472d-f66b-7350-a159-a3d5cdea6ef7"]}`.
A conversa nova sobe com `mcp_statuses: loaded` e as 45 tools (hoje **48**).

**Efeito colateral.** Todo conversation novo desse assistant passa a carregar o
`mcp-cad-server` — e o AutoCAD precisa estar aberto (senão cai em `ezdxf` ou dá erro).

---

## 28. MTEXT não quebra linha (`_q` come o `\`)

**Sintoma.** `entity_create_mtext` com `\P` entre as linhas desenha tudo numa linha só,
com `/P` no meio do texto.

**Causa.** `_q()` faz `.replace("\\", "/")` para virar literal AutoLISP — qualquer barra
invertida morre antes de chegar ao AutoCAD.

**Contorno.** Uma `entity_create_text` por linha (foi o que a legenda do teste usou: 12
textos + 1 retângulo). Correção definitiva: aceitar um marcador (ex.: `~P`) e trocar por
`\P` depois do escape.

---

## 29. `(error "...")` NÃO existe em AutoLISP

**Sintoma.** A validação que eu tinha colocado no `layer_create` (para falhar com tipo de
linha inexistente) voltou como **`no function definition: ERROR`** em vez da mensagem.

**Causa.** `error` não é função do AutoLISP puro (é conceito do VLISP/`*error*`). Testado
também `functionp`: também não existe. O `(error ...)` nunca abortou nada — o "não aborta
dentro do progn" que estava documentado era só isso: a função não existe e a chamada falha
com aquela mensagem, sem parar a execução.

**Correção (aplicada).** O LISP devolve a string `"MCPERRO:<mensagem>"` e `_aval` converte
em `ok=false, error=<mensagem>`. Use esse padrão em qualquer validação nova:

```python
'(if <condicao-de-erro>'
' (strcat "MCPERRO:mensagem clara")'
' (progn ...resultado...))'
```

---

## 30. `-LINETYPE _LOAD` trava o AutoCAD para sempre

**Sintoma.** `layer_linetype_load` (primeira versão, via `(command "_.-LINETYPE" "_LOAD" ...)`)
fez o `SendCommand` **não retornar**; depois disso **toda** chamada COM dava
`RPC_E_CALL_REJECTED` e o teste seguinte já começava com o AutoCAD "morto".

**Causa.** O `-LINETYPE` pede um **ENTER extra** no fim (loop de "Enter linetype name:").
Sem esse Enter a linha de comando fica esperando e o AutoCAD não processa mais COM.

**Correção (aplicada).** `layer_linetype_load` usa a API COM `doc.Linetypes.Load(nome, arquivo)`
e confirma com `doc.Linetypes.Item(nome)` — sem passar pela linha de comando.

**Regra geral.** Prefira a API COM (`doc.Linetypes`, `doc.Layers`, `doc.Blocks`) a
`(command ...)` para qualquer coisa "de configuração". Comando interativo no `SendCommand`
é a maior fonte de AutoCAD travado.

---

## 31. PNG do desenho: 160x28 e `path` ignorado

**Sintoma (relatado pelo agente).** `view_render_png`/`view_screenshot` devolviam
`ok=true`, ignoravam o `path` pedido e gravavam um PNG de **160x28 px**.

**Causa dupla.** (1) A captura usava `PrintWindow` com a janela **minimizada** — o Windows
devolve um bitmap do tamanho do ícone. (2) O tool procurava `payload["data"]` (bytes), mas
o backend devolve `payload["png"]` (caminho do arquivo) — caía no `return {"ok": True,
"payload": ...}` e nunca copiava para o `path`.

**Correção (aplicada).** `capturar()` restaura a janela (`IsIconic` + `ShowWindow`) e falha
com mensagem clara se a área útil for < 320x240; o tool copia o PNG para o `path` e devolve
`largura`/`altura`. Testado: 1026x689 e 1382x744 px.

---

## 32. Plot com escala REAL (1:50) — `folha` e `escala`

**Antes.** Sempre A4 "fit": 22 m viravam 197 mm → **1:111**.

**Agora.** `drawing_plot_pdf(path, folha="A2", escala=50)`:

- calcula a extensão real com `ZoomExtents` + `EXTMIN`/`EXTMAX` (e restaura a vista);
- converte unidade→mm por `INSUNITS` (6 = metros → 1000 mm/unidade);
- **escolhe a folha** (A4…A0) que couber quando `folha` não é dada;
- valida antes de plotar e, se não couber, devolve `ok=false` dizendo o tamanho necessário
  e qual folha/escala usar (não plota cortado em silêncio);
- `SetCustomScale` é aplicado **por último** (qualquer `setattr` de layout depois volta o
  "fit" e perde a escala);
- gira 90° (`PlotRotation`) quando o desenho é "deitado" e a folha é retrato.

**Medido.** Prancha 22 x 12 m em 1:50 → conteúdo **489,8 x 311,1 mm** num A2 paisagem
(594x420). A4 recusa: "precisa 489x311 mm… use folha=A2".

**PDF aberto no visualizador.** O plot grava em `<nome>_tmp_plot.pdf` ao lado, tenta copiar
por cima do destino e devolve `aviso` + o caminho do arquivo que existe. Não perde o plot.

**Texto continua vetorizado** no PDF (é o plotter DWG To PDF) — não é texto selecionável.

---

## 33. `quantitativo()` devolvendo desenho VAZIO com `ok=true`

**Sintoma.** 0 entidades, `INSUNITS=4`, só camadas `0`/`Defpoints`, sem erro — duas vezes.

**Causa.** O COM caiu, o AutoCAD criou/ativou **outro** desenho (um `Drawing1` ou um
`stage_*.dwg` do export de DXF). O quantitativo lia o documento ativo, que era vazio.

**Correção (aplicada).** O tool agora lê `drawing_info` antes, devolve `documento`,
`caminho` e `entidades_no_autocad` no resultado e, se o DXF sair com 0 entidades, retorna
`ok=false` dizendo **qual** documento foi lido e que o DWG desenhado não é o ativo.

**Dica operacional.** Antes de medir/plotar, confira `inspect_drawing`: se o nome não for o
do seu DWG, chame `open` nele (ou feche os `Drawing1` extras). Se o nome estiver certo e o
DXF sair vazio, o problema é outro: veja a armadilha 35 (accoreconsole lendo disco atrasado).

---

## 34. COM `Call was rejected` — agora tem ESC de verdade

**Sintoma.** `(-2147418111, 'Call was rejected by callee.')` em cadeia, mesmo com um único
agente, depois de um comando que ficou pendente na linha de comando.

**Causa.** O `_esc()` antigo fazia só `PostMessage(WM_KEYDOWN, VK_ESCAPE)` na janela — não
adianta com o AutoCAD em prompt ativo.

**Correção (aplicada).** `enviar_esc(forcado=True)`: `ShowWindow(SW_RESTORE)` +
`SetForegroundWindow`, confere que o AutoCAD está em foco (`GetForegroundWindow`) e só
então manda ESC via `keybd_event` (teclado real). As tentativas caíram de 40 para 16
(`MCP_CAD_COM_TENTATIVAS`) e o ESC acontece a cada 4 recusas.

**Limite.** Se o prompt for de um comando que ignora ESC (raro), feche o desenho sem salvar
ou reinicie o AutoCAD. Evite `(command ...)` interativo (armadilha 30).

---

## 35. DXF exportado do DISCO vem vazio/atrasado (`quantitativo` mentindo)

**Sintoma.** O AutoCAD diz "204 entidades", `quantitativo()` devolve 0 (ou o desenho de
ontem) e o DXF gerado tem `BLOCKS`/`LAYERS` mas nenhuma entidade no model space.

**Causa.** A exportação ia por `accoreconsole.exe`, que **lê o DWG do disco**. Se o desenho
tem alterações não salvas — ou nunca foi salvo, e o `FullName` aponta para um arquivo que
não existe em `...\Arquimedes\arquimedes\<nome>` — o accoreconsole converte a versão antiga
(vazia) e o DXF nasce vazio. Alem disso o `-WBLOCK` de fallback travava o prompt.

**Correção (aplicada).** O `drawing_save_as_dxf` agora tenta primeiro `doc.Export` por COM,
**na memória**, com `SelectionSet` (`ss.Select(5)` = todas as entidades):

```python
ss = doc.SelectionSets.Add("MCP_EXPORT_DXF")
ss.Select(5)                       # acSelectionSetAll
doc.Export(base_sem_extensao, "DXF", ss)   # AutoCAD ACRESCENTA ".dxf"
ss.Delete()
```

Funciona também em desenho **nunca salvo** (não precisa de DWG em disco). O accoreconsole
ficou como fallback e, se for usado, o desenho é salvo antes (com `aviso` no payload).

**Detalhes que queimam.**
- `Export(FileName, "DXF", ss)` **concatena** a extensão: passe `...\nome` e o arquivo sai
  como `...\nome.dxf`. Se passar `...\nome.dxf` sai `nome.dxf.dxf` (ou nada, dependendo da
  versão) — por isso o código exporta sem sufixo e depois move.
- `ss.Select(5)` funciona com o argumento único; se falhar, `ss.Select()` seleciona tudo.
- `doc.Save` antes da rota accoreconsole é obrigatório: sem isso o DXF continua atrasado.
- Consequência para o teste: para medir o que está na tela, **não** salve, exporte e meça —
  exporte por COM direto da memória.
- **Efeito colateral do fallback antigo (o que o reteste viu):** o `SaveAs` para
  `stage_*.dwg` **troca o caminho do documento ativo** — depois de um `quantitativo()`, o
  documento aberto passa a se chamar `stage_8736d3c6_153139.dwg` e o usuário acha que o
  desenho sumiu. Com o export COM em primeiro lugar isso não acontece mais (medido: nome e
  `FullName` intactos depois do `quantitativo()`). No fallback, o payload traz `aviso`.
- Estágios se acumulavam (11 `stage_*.dwg` em `C:\temp\mcp_cad_com` num dia). O
  `_estagio_sem_espaco` agora apaga os `stage_*` com mais de 24 h antes de criar o próximo
  (os do dia ficam: podem ser o arquivo de trabalho de um desenho aberto).
- **Desenho nunca salvo tem `FullName` VAZIO** (não é só um caminho inexistente): é o caso
  que discrimina. `drawing_new()` sem nome → `FullName == ""` → `doc.Export` por COM exporta
  as 2 entidades; qualquer rota que dependa de arquivo em disco falha.


