# Faixa de cotas auxiliares de profundidade — piloto 10 × 20 m

O gerador coloca a dimensão **dentro** do ambiente sempre que for
graficamente viável. Quando portas, mobiliário e rótulos impedem uma linha
vertical interna, ele utiliza uma **referência de cota exterior ao desenho
da planta**, com os mesmos `y1/y2` e o mesmo comprimento físico do modelo.

Não desenha linhas de chamada atravessando cômodos, não altera a posição
das paredes, não cria uma segunda geometria de residência. O rótulo
`AUX DXX {ambiente} {valor} m` relaciona explicitamente a referência
gráfica ao ambiente cadastrado. O aviso `COTAS AUX. - REFERENCIA SEM CHAMADA`
impede interpretar a barra como uma cota diretamente encostada à parede.

**No caso piloto:**
- Larguras cotadas dentro dos ambientes: **7/7**.
- Profundidades cotadas dentro dos ambientes: **5/7**.
- Profundidades na faixa auxiliar: **2/7** (lavanderia e banheiro).
- Profundidades sem representação gráfica: **0/7**.
- Dimensões em tabela: **7/7** nos dois eixos.

O relatório MCP/ZIP distingue `depth_dimensions_inside_drawn=5`,
`depth_dimensions_auxiliary_drawn=2` e
`graphic_status=complete_with_auxiliary`. Nunca declarar
`7/7` como cotas internas em situ.

Esta representação proporcional é um auxílio **preliminar** de leitura.
No projeto executivo a localização e as linhas de chamada de cada cota
devem ser definidas por projetista, e a prancha conferida em impressão.
O método não verifica NBR, acessibilidade ou condições municipais.

### Testes

`test_cotas_profundidade_auxiliar.py` mede o comprimento real da barra,
comprova que a faixa não atravessa paredes/móveis e exige nomes e medidas
nos rótulos; a exportação do pacote deve continuar a funcionar sem erros.
