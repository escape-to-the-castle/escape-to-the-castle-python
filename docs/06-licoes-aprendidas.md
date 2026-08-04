# 6. Lições Aprendidas

Esta seção registra os problemas, desafios e erros desta primeira semana de projeto —
dedicada ao planejamento, à documentação e à organização do repositório — e o aprendizado
extraído de cada um deles.

## 6.1 Problemas e Desafios Enfrentados

### Requisitos inicialmente vagos demais para serem testáveis
A primeira redação dos requisitos, herdada de relatórios anteriores, continha itens como
"o jogo deve ter um sistema de vidas" — descrição que não permite construir um caso de
teste objetivo. Ao preencher a coluna *Teste* da Tabela 1, o grupo percebeu que vários
requisitos precisavam ser reescritos com valores concretos (3 vidas iniciais, 3 portais por
nível, decremento de exatamente 1 unidade).

> **Aprendizado:** escrever o teste junto com o requisito é o melhor filtro de qualidade
> para a especificação. Requisito que não gera teste claro é requisito mal escrito.

### Regras de negócio implícitas e não documentadas
Questões como "o que acontece se o jogador errar a última pergunta e perder a última vida?"
ou "um portal já usado pode ser acionado de novo?" não estavam registradas em lugar nenhum,
existindo apenas como suposição na cabeça de cada integrante. Elas só emergiram ao desenhar
a máquina de estados da Figura 2.

> **Aprendizado:** o esforço de desenhar o diagrama força a explicitar decisões que a
> descrição textual permite deixar em aberto. O diagrama funcionou como instrumento de
> descoberta de requisitos, não apenas de comunicação.

### Tendência a acoplar conteúdo e lógica
A proposta inicial embutia as perguntas diretamente no código do jogo. Ao confrontar essa
escolha com o requisito de modificabilidade (**RNF06**), ficou evidente que qualquer nova
questão exigiria alterar e recompilar o programa.

> **Aprendizado:** separar dados de lógica é uma decisão barata quando tomada no
> planejamento e cara quando adiada. Os requisitos não-funcionais da ISO 25010 se mostraram
> úteis exatamente por antecipar esse tipo de custo.

### Fronteiras de responsabilidade entre módulos
Houve dificuldade em decidir onde alocar a verificação de derrota: no Gerenciador de Vidas,
no Módulo de Perguntas ou no estado CENÁRIO. Cada alternativa foi discutida quanto ao
número de transições resultantes na máquina de estados.

> **Aprendizado:** decisões arquiteturais devem ser avaliadas pelo que simplificam, e não
> apenas pelo que permitem. Concentrar a verificação em um único estado reduziu tanto o
> código quanto a quantidade de casos de teste necessários.

### Organização do repositório e versionamento
O grupo teve de aprender o fluxo de *Releases* do GitHub e a convenção de versionamento
semântico, além de definir uma estrutura de pastas que sobrevivesse ao crescimento do
projeto sem exigir reorganização posterior.

> **Aprendizado:** definir a estrutura do repositório e o padrão de commits antes do início
> da codificação evita retrabalho de reorganização e mantém o histórico legível desde a
> primeira Release.

## 6.2 Consolidação de Conceitos

- **ISO/IEC 25010** — a norma deixou de ser uma lista abstrata de características e passou a
  funcionar como um roteiro de perguntas ("este sistema precisa ser modificável? tolerante a
  falhas?") que revelou requisitos não percebidos.
- **Padrões de arquitetura de jogos** — os padrões *Game Loop* e *State* ofereceram uma
  solução pronta e testada para o problema central do projeto, que é a alternância entre
  dois contextos de jogo muito diferentes.
- **Rastreabilidade** — vincular cada módulo aos requisitos que ele atende (Seção 4.3)
  tornou visível que nenhum requisito ficou sem responsável e que nenhum módulo existe sem
  justificativa.

## 6.3 Refinamentos Adotados para as Próximas Semanas

| Aspecto | Refinamento planejado |
|---------|------------------------|
| Planejamento de testes | Registrar as evidências (capturas de tela) no momento da execução do teste, e não ao final da semana, evitando reexecuções. |
| Método de trabalho | Vincular toda Issue ao identificador do requisito correspondente da Tabela 1, garantindo rastreabilidade requisito → código → teste. |
| Método experimental | Implementar o contador de FPS já no primeiro protótipo jogável, para que **RNF02** possa ser medido continuamente e não apenas ao final. |
| Especificação | Revisar a Tabela 1 ao início de cada semana, incorporando as regras de negócio descobertas durante a implementação. |
| Documentação | Manter os arquivos Markdown atualizados no mesmo Pull Request que altera o código, evitando defasagem entre documento e sistema. |
