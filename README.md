# Matching Engine

Matching engine em Python para um único ativo, com livro de ofertas em memória e interface pelo terminal. O projeto recebe ordens de compra e venda, encontra ofertas compatíveis e informa o preço e a quantidade negociados.

## O problema

Uma ordem representa o interesse em comprar ou vender uma quantidade de um ativo. Para existir uma negociação, uma compra precisa encontrar uma venda com preço compatível.

O sistema precisa resolver duas perguntas: **qual ordem deve ser atendida primeiro?** e **quanto pode ser negociado?**

Considere este livro:

~~~text
Ordens de Compra     | Ordens de Venda
--------------------|----------------
100 @ 10             | 100 @ 20
                     | 200 @ 20
~~~

A compra a 10 não encontra uma venda compatível: os vendedores pedem 20. As ordens ficam no livro esperando uma contraparte.

Se chegar uma compra a mercado de 150 unidades, ela aceita o melhor preço de venda disponível. A engine consome primeiro a venda de 100 unidades e depois 50 unidades da segunda venda. O saldo dessa segunda ordem passa a ser 150.

A saída agrega as execuções feitas no mesmo preço:

~~~text
Trade, price: 20, qty: 150
~~~

Embora apareça uma única linha, as ordens foram atendidas individualmente e na ordem correta. A agregação é apenas uma escolha de apresentação.

## Escopo e requisitos

| Requisito | Comportamento implementado |
| --- | --- |
| Um ativo | Todas as ordens pertencem ao mesmo ativo; não existe campo de símbolo. |
| Ordem limit | Executa em preços compatíveis e mantém o saldo no livro. |
| Ordem market | Executa imediatamente com a liquidez disponível; o saldo não executado é descartado. |
| Memória volátil | Ordens abertas ficam em um dicionário; encerrar o processo perde o estado. |
| Melhor preço | Compra encontra a menor venda; venda encontra a maior compra. |
| Ordem de chegada | No mesmo preço, a menor sequência de chegada executa primeiro. |
| Visualização | Os comandos book, print book e book ids mostram o livro. |
| Cancelamento | Remove uma ordem aberta usando seu identificador. |
| Alteração | Altera preço, quantidade restante ou ambos. |
| Pegged | Compra acompanha o bid regular; venda acompanha o offer regular. |
| Saída dos trades | Usa Trade, price: <preço>, qty: <quantidade>. |

O programa é sequencial. Não usa banco de dados, servidor, infraestrutura de nuvem, dependências externas ou threads.

## Por que Python

Python permite expressar as regras com classes pequenas, listas, dicionários e testes da biblioteca padrão. Isso deixa o trabalho concentrado no comportamento do livro.

A escolha se aplica a este desafio, que não pede metas de latência ou volume de ordens. Ela não pressupõe que esta estrutura tenha o desempenho de uma exchange em produção. Java, C++ e outras linguagens também poderiam resolver o problema; aqui, clareza e facilidade de verificação pesam mais.

A implementação usa apenas:

- dataclasses para representar uma ordem e um trade;
- decimal para trabalhar com preços decimais;
- unittest para testar os comportamentos.

## Requisitos para executar

Python **3.10 ou superior**. A sintaxe de tipos como Decimal | None exige essa versão. Não há pacotes para instalar e não é necessário executar pip install.

Na pasta do projeto:

~~~powershell
python --version
python matching_engine.py
~~~

No Windows, se você usa o launcher do Python:

~~~powershell
py -3 matching_engine.py
~~~

O terminal deve mostrar:

~~~text
Matching Engine ready. Type 'help' for commands.
>>>
~~~

Digite os comandos depois do prompt. Não digite o próprio símbolo >>>. Cada nova execução do programa inicia um livro vazio e reinicia os identificadores.

## Comandos

| Comando | Exemplo | Efeito |
| --- | --- | --- |
| limit <buy ou sell> <price> <qty> | limit buy 10 100 | Compra limitada a 10, com 100 unidades. |
| market <buy ou sell> <qty> | market buy 150 | Compra com o melhor preço disponível. |
| peg bid buy <qty> | peg bid buy 150 | Compra que acompanha o melhor bid regular. |
| peg offer sell <qty> | peg offer sell 150 | Venda que acompanha o melhor offer regular. |
| cancel [order] <id> | cancel order order_1 | Cancela uma ordem aberta. |
| amend [order] <id> price <valor> | amend order_1 price 9.98 | Altera o preço. |
| amend [order] <id> qty <valor> | amend order_1 qty 80 | Define a nova quantidade restante. |
| amend [order] <id> price <valor> qty <valor> | amend order_1 price 9.98 qty 80 | Altera preço e quantidade. |
| book | book | Mostra as ordens por preço e chegada. |
| book ids | book ids | Inclui os identificadores no livro. |
| print book | print book | Outra forma de mostrar o livro. |
| help | help | Lista a sintaxe dos comandos. |
| exit ou quit | exit | Encerra o programa. |

A palavra order é opcional em cancel e amend. Nos comandos, buy significa compra e sell significa venda. Use ponto para separar casas decimais: 9.99, e não 9,99.

Os identificadores seguem order_1, order_2 etc. Uma ordem market também consome um identificador interno, mas ele não é mostrado, pois essa ordem não permanece no livro. Por isso, os IDs visíveis podem ter intervalos.

## Exemplo completo do enunciado

Inicie o programa com um livro vazio:

~~~text
>>> limit buy 10 100
Order created: buy 100 @ 10 order_1
>>> limit sell 20 100
Order created: sell 100 @ 20 order_2
>>> limit sell 20 200
Order created: sell 200 @ 20 order_3
>>> market buy 150
Trade, price: 20, qty: 150
>>> market buy 200
Trade, price: 20, qty: 150
>>> market sell 200
Trade, price: 10, qty: 100
~~~

A primeira compra a mercado encontra 300 unidades de venda e negocia 150. A segunda encontra somente as 150 restantes: as 50 unidades que faltam para completar seu pedido não entram no livro. A venda a mercado encontra apenas a compra de 100 unidades a 10 e também descarta seu saldo.

Ao final, o livro está vazio.

## Como a solução funciona

### Representação de uma ordem

A classe Order armazena:

| Campo | Para que serve |
| --- | --- |
| id | Identificar uma ordem em cancelamentos e alterações. |
| side | Indicar compra ou venda. |
| price | Guardar o preço limite ou o preço atual de uma pegged; None representa ausência de preço. |
| qty | Guardar a quantidade ainda aberta, não a quantidade original. |
| sequence | Representar a posição de chegada para desempatar ordens no mesmo preço. |
| peg_reference | Indicar bid ou offer; None identifica uma ordem sem vínculo automático. |

Order e Trade usam dataclass para criar automaticamente o construtor. Não precisam de herança, fábricas ou classes diferentes para cada tipo de ordem.

A engine guarda as ordens abertas em self.orders, um dicionário que associa o ID ao objeto Order. Uma ordem preenchida ou cancelada é removida desse dicionário. Uma pegged sem referência continua cadastrada, mas fica fora das ofertas executáveis.

### Prioridade por preço e chegada

O método book_orders filtra um lado do livro e ordena as ordens por dois critérios:

~~~python
# Compra: maior preço primeiro; empate pela menor sequência.
(-order.price, order.sequence)

# Venda: menor preço primeiro; empate pela menor sequência.
(order.price, order.sequence)
~~~

O sinal negativo na compra inverte a ordenação do preço. A sequência desempata preços iguais. Assim, a regra de FIFO não depende do acaso nem da ordem em que o dicionário é percorrido.

Um contador de sequência é suficiente porque os comandos são processados um por vez. Usar horário de sistema não melhoraria a regra e poderia gerar empates entre ordens recebidas no mesmo instante.

### Encontrar e executar uma contraparte

O método _match recebe uma ordem nova ou alterada e repete estes passos:

1. Busca o lado oposto do livro.
2. Escolhe a primeira ordem depois da ordenação por preço e chegada.
3. Verifica se o preço atende ao limite da ordem recebida, quando existir um limite.
4. Calcula a quantidade negociada usando min(incoming.qty, resting.qty).
5. Diminui a quantidade das duas ordens.
6. Remove a contraparte se sua quantidade chegar a zero.
7. Atualiza as referências das pegged e procura a próxima contraparte.

O loop termina quando a ordem recebida é preenchida, quando não existe contraparte ou quando o melhor preço disponível excede seu limite.

Se o melhor preço já não serve para uma limit, os demais também não servem: eles aparecem depois justamente por terem preços menos favoráveis.

### Preço da negociação

A negociação usa o preço da ordem que já estava no livro.

Se existe uma venda de 80 unidades a 10 e chega uma compra limit de 100 unidades a 11, a engine negocia 80 a 10. O comprador aceita pagar até 11, mas encontra uma oferta melhor a 10. As 20 unidades restantes ficam no livro a 11.

~~~text
>>> limit sell 10 80
Order created: sell 80 @ 10 order_1
>>> limit buy 11 100
Trade, price: 10, qty: 80
Order created: buy 20 @ 11 order_2
~~~

Essa é a justificativa para **executar limit orders que cruzam o livro**, uma das alternativas permitidas pelo enunciado. Ignorar essas ordens também seria permitido pelo desafio, mas executar permite respeitar o limite e aproveitar a liquidez existente.

### Preços com Decimal

Os preços são criados a partir de texto, por exemplo Decimal("9.99"). Isso evita introduzir a aproximação binária de um float na leitura dos comandos.

A engine compara e ordena preços; não calcula taxas, valor financeiro total ou arredondamento monetário. Não há regra de tick size ou limite de casas decimais neste projeto. Preços precisam ser positivos e finitos.

### Quantidade restante e preenchimento parcial

qty representa o que ainda falta executar. Uma venda com qty 200 que negocia 50 passa a ter qty 150.

A quantidade de cada negociação é o menor dos dois saldos. Isso impede consumir mais unidades do que uma ordem oferece ou deseja executar.

Uma ordem limit parcialmente executada permanece com o saldo. Uma ordem market parcialmente executada termina: o saldo é descartado. Uma market sem contraparte retorna No trades.

### Agregação da saída

Trade registra preço e quantidade. Quando duas execuções consecutivas usam o mesmo preço, suas quantidades são somadas para reproduzir a saída do desafio.

Execuções em preços diferentes geram linhas diferentes:

~~~text
Trade, price: 20, qty: 50
Trade, price: 21, qty: 100
~~~

Não existe um histórico permanente de trades, nem IDs das duas contrapartes dentro de Trade. Os trades do comando são devolvidos para exibição e podem ser usados pelos testes.

## Cancelamento

cancel_order procura o ID no dicionário. Se ele existe, a engine remove a ordem e atualiza as pegged que possam depender dela.

~~~text
>>> limit buy 10 100
Order created: buy 100 @ 10 order_1
>>> cancel order order_1
Order cancelled
>>> cancel order order_1
Order not found
~~~

O segundo cancelamento não muda o livro. O mesmo vale para um ID desconhecido ou para uma ordem já totalmente preenchida.

## Alteração de ordens

amend_order valida os valores antes de alterar o estado. Uma alteração inválida não deve deixar metade da modificação aplicada.

O ID da ordem permanece o mesmo. A quantidade informada substitui o **saldo restante**. Se uma ordem criada com 100 unidades já executou 20, alterar qty para 60 significa deixar 60 unidades abertas.

| Alteração | Prioridade |
| --- | --- |
| Preço diferente | Recebe uma nova sequência. |
| Aumento de quantidade | Recebe uma nova sequência. |
| Redução de quantidade, sem mudar preço | Preserva a sequência. |
| Mesmo preço e mesma quantidade | Preserva a sequência. |

A mudança de preço perde prioridade no novo nível. Aumentar quantidade também perde prioridade para impedir que uma posição antiga passe a reservar mais unidades na frente das demais. Reduzir quantidade preserva a prioridade porque diminui a oferta que estava na frente.

Exemplo do enunciado, em uma sessão nova:

~~~text
>>> limit buy 10 200
Order created: buy 200 @ 10 order_1
>>> limit buy 9.99 100
Order created: buy 100 @ 9.99 order_2
>>> limit sell 10.5 100
Order created: sell 100 @ 10.5 order_3
>>> amend order_1 price 9.98
Order amended: buy 200 @ 9.98 order_1
>>> book
Ordens de Compra     | Ordens de Venda
--------------------|----------------
100 @ 9.99           | 100 @ 10.5
200 @ 9.98           |
~~~

A visualização ordena o preço atualizado, por isso a ordem de 200 unidades aparece abaixo da compra a 9.99. Se já houvesse uma compra a 9.98, ela ficaria antes da ordem alterada por ter uma sequência mais antiga.

Uma alteração também pode tornar uma limit agressora. Nesse caso, a ordem alterada executa as contrapartes compatíveis e seu saldo retorna ao livro. qty 0 não cancela uma ordem; para remover a ordem, use cancel.

## Ordens pegged

### Referência e combinações aceitas

Bid é o melhor preço de compra. Offer é o melhor preço de venda. A implementação aceita as combinações passivas ilustradas pelo desafio:

- peg bid buy acompanha o maior preço de uma compra limit regular;
- peg offer sell acompanha o menor preço de uma venda limit regular.

peg bid sell e peg offer buy são rejeitadas. Suportar essas combinações exigiria definir também o comportamento de pegged agressoras, que não faz parte desta implementação.

A referência considera somente ordens **não pegged**. Se uma pegged definisse a própria referência, ela poderia manter sozinha um preço mesmo depois de desaparecer a ordem que justificava aquele preço.

Essa é uma convenção explícita para os pontos que o enunciado não detalha. Uma regra diferente de referência exigiria ajustar o método _refresh_pegged_orders e os testes correspondentes.

### Atualização e prioridade

Depois de inserir, cancelar ou alterar uma ordem, a engine recalcula o bid e o offer regulares. Também faz isso entre preenchimentos dentro de um mesmo comando, pois consumir uma ordem pode mudar a referência da próxima execução.

A atualização automática do preço de uma pegged preserva sua sequência original. Essa regra segue o exemplo do enunciado:

~~~text
>>> limit buy 10 200
Order created: buy 200 @ 10 order_1
>>> limit buy 9.99 100
Order created: buy 100 @ 9.99 order_2
>>> limit sell 10.5 100
Order created: sell 100 @ 10.5 order_3
>>> peg bid buy 150
Order created: buy 150 peg bid @ 10 order_4
>>> limit buy 10.1 300
Order created: buy 300 @ 10.1 order_5
>>> book
Ordens de Compra     | Ordens de Venda
--------------------|----------------
150 @ 10.1           | 100 @ 10.5
300 @ 10.1           |
200 @ 10             |
100 @ 9.99           |
~~~

A pegged passa para 10.1 e aparece antes da nova compra de 300 unidades: ela entrou antes e conservou sua sequência. Isso é diferente de uma alteração manual de preço, que perde prioridade.

### Ausência de referência

Se não existe uma limit regular do lado de referência, a pegged fica com price = None. Ela permanece cadastrada, pode ser cancelada ou ter sua quantidade alterada, mas não participa do matching.

O livro mostra essas ordens abaixo das ofertas:

~~~text
Waiting reference: order_1 peg bid buy 150
~~~

Quando surgir uma referência regular, a pegged volta a ter preço e participa do livro. A ausência de preço nessa ordem **não** a transforma em market.

Essa regra tem uma consequência observável: se o único bid regular for totalmente consumido, uma pegged to bid fica aguardando referência, mesmo que ainda tenha quantidade. Uma market remanescente não pode executá-la enquanto ela estiver sem referência. Se houver outro bid regular, a pegged acompanha esse novo preço antes da próxima execução.

### Alteração de uma pegged

Alterar somente qty mantém o vínculo com bid ou offer, aplicando a regra de aumento ou redução de prioridade.

Informar explicitamente price converte a ordem para uma limit regular. Ela deixa de acompanhar a referência e passa a usar o preço informado. O mesmo ID é mantido. Se o novo preço for diferente do atual, perde prioridade; se a quantidade aumentar, também perde.

## Validação e mensagens

O programa rejeita side desconhecido, quantidade não inteira ou não positiva, preço não positivo ou não finito, referência pegged inválida e comandos com formato incorreto.

As validações existem nos métodos da engine, além das conversões na interface. Assim, chamar os métodos diretamente em Python também verifica os dados.

Erros de entrada são exibidos como Error: <mensagem>. O programa continua recebendo comandos. Uma linha vazia não faz nada. Ctrl+C, fim da entrada e exit encerram o loop.

## Organização do projeto

~~~text
matching_engine.py       Modelos, engine, validações e interface pelo terminal.
test_matching_engine.py  Testes automatizados de comportamento.
README.md                Problema, uso, regras e decisões.
COMMIT_GUIDE.md          Tutorial de reconstrução por etapas com código e commits.
.gitignore               Arquivos temporários que não entram no Git.
~~~

A engine e a interface ficam no mesmo arquivo para manter o tamanho do projeto proporcional ao desafio. A função execute_command traduz texto em chamadas aos métodos; a função main cuida de input e print. Importar MatchingEngine nos testes não abre o terminal, porque main só roda no bloco if __name__ == "__main__".

## Testes

Execute na pasta do projeto:

~~~powershell
python -m unittest -v
~~~

No Windows, com o launcher do Python:

~~~powershell
py -3 -m unittest -v
~~~

A suíte contém 21 testes. Eles verificam resultados e estado do livro, incluindo:

- ordenação por preço e chegada e FIFO observado no saldo de cada ordem;
- execução em vários preços, falta de liquidez e descarte de saldo market;
- limit agressora, preço da contraparte e saldo limit;
- cancelamento e identificadores ausentes;
- mudança de preço, aumento e redução de quantidade;
- alteração que cruza o livro e alteração inválida sem efeito parcial;
- peg to bid, peg to offer, atualização após cancelamento e entre trades;
- pegged aguardando referência, reativação e conversão para limit;
- validações, comandos do enunciado e exibição de IDs.

Cada teste cria uma engine nova. Isso evita que o resultado de um teste dependa das ordens de outro.

## Custo e limites da estrutura

Com N ordens abertas, o dicionário permite localizar e remover uma ordem por ID em tempo médio O(1). O cancelamento completo também recalcula referências, portanto seu custo total é O(N).

book_orders filtra e ordena ordens, com custo O(N log N) no pior caso. render_book faz essa ordenação para os dois lados e monta o texto.

O matching ordena novamente antes de cada preenchimento para respeitar mudanças nas pegged. Com F preenchimentos, o custo é O(F * N log N) no pior caso. O armazenamento das ordens abertas é O(N).

Essa escolha privilegia uma única fonte de dados e facilita cancelamentos, alterações e explicação da prioridade. Ela funciona para o escopo de um desafio pequeno. Para um volume maior, uma evolução seria guardar níveis de preço ordenados e filas por nível, evitando ordenar todas as ordens a cada preenchimento.

Não foram implementados concorrência, persistência, vários ativos, taxas, saldo de clientes, auditoria individual de execuções, tick size ou garantias de latência. Esses recursos exigiriam regras e estruturas adicionais.

## Construir por etapas

O COMMIT_GUIDE.md apresenta um roteiro de estudo e reconstrução. Cada etapa informa o arquivo que deve ser criado ou substituído, traz o código completo daquela versão, explica as partes novas, mostra o teste esperado e indica um commit correspondente.

As etapas são cumulativas e chegam aos arquivos desta pasta. O roteiro deve ser executado em uma pasta separada, para preservar esta versão pronta enquanto você acompanha a construção.