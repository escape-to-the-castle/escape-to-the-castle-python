# 3. Especificação de Requisitos e Testes

Esta seção apresenta os requisitos funcionais (RF) e não-funcionais (RNF, classificados
segundo a norma **ISO/IEC 25010**) do jogo **Fuga para o Castelo**, refinados a partir dos
relatórios anteriores, junto aos testes associados a cada requisito.

> **Nota sobre o preenchimento:** por se tratar da entrega de **planejamento** da Semana 1,
> as colunas *Resultado Obtido* e *Evidências de Resultados* estão marcadas como pendentes
> e serão preenchidas conforme a implementação e a execução dos testes avançarem.

## Tabela 1 — Requisitos e Testes Planejados

| Requisito | RF ou RNF | Teste | Resultado Esperado | Resultado Obtido | Evidências de Resultados |
|---|---|---|---|---|---|
| **RF01** — O príncipe deve se movimentar lateralmente pelo cenário. | RF | Pressionar as teclas de direção e observar o deslocamento do personagem. | O personagem desloca-se de forma contínua e coerente com a tecla pressionada. | *Pendente* | *Pendente* |
| **RF02** — O príncipe deve ser capaz de saltar. | RF | Pressionar a tecla de salto em solo e em pleno ar. | O salto ocorre apenas quando o personagem está em solo, com trajetória e retorno consistentes. | *Pendente* | *Pendente* |
| **RF03** — O cenário deve conter obstáculos (pedras e árvores). | RF | Percorrer um nível completo registrando os obstáculos renderizados. | Pedras e árvores aparecem nas posições definidas pelo nível e são visualmente distinguíveis. | *Pendente* | *Pendente* |
| **RF04** — O jogo deve detectar colisão entre o príncipe e obstáculos. | RF | Conduzir o personagem deliberadamente contra uma pedra e contra uma árvore. | A colisão é detectada em ambos os casos e aciona a penalidade de vida. | *Pendente* | *Pendente* |
| **RF05** — Cada nível deve conter exatamente 3 portais. | RF | Percorrer o nível do início ao castelo contando os portais encontrados. | Exatamente 3 portais são encontrados ao longo do percurso. | *Pendente* | *Pendente* |
| **RF06** — O contato com um portal deve transportar o jogador ao mundo de perguntas. | RF | Conduzir o personagem até cada um dos 3 portais. | Em cada contato, o jogo transita do estado CENÁRIO para o estado PERGUNTAS. | *Pendente* | *Pendente* |
| **RF07** — Cada portal deve abrir uma questão de múltipla escolha com alternativas de "a" a "d". | RF | Entrar em um portal e inspecionar a tela de pergunta exibida. | Enunciado e exatamente quatro alternativas rotuladas de "a" a "d" são apresentados. | *Pendente* | *Pendente* |
| **RF08** — O jogo deve validar a alternativa escolhida pelo jogador. | RF | Responder uma questão de gabarito conhecido, uma vez corretamente e uma vez incorretamente. | O acerto é reconhecido como correto e o erro como incorreto, com feedback ao jogador. | *Pendente* | *Pendente* |
| **RF09** — O jogador deve iniciar a partida com 3 vidas. | RF | Iniciar uma nova partida e inspecionar o HUD. | O HUD exibe 3 vidas ao início da partida. | *Pendente* | *Pendente* |
| **RF10** — Errar uma pergunta deve reduzir uma vida. | RF | Responder incorretamente a questão de um portal e comparar o HUD antes e depois. | A contagem de vidas é decrementada em exatamente 1 unidade. | *Pendente* | *Pendente* |
| **RF11** — Colidir com um obstáculo deve reduzir uma vida. | RF | Colidir uma única vez com uma pedra e comparar o HUD antes e depois. | A contagem de vidas é decrementada em exatamente 1 unidade. | *Pendente* | *Pendente* |
| **RF12** — Após responder, o jogador deve retornar ao cenário no ponto do portal. | RF | Responder à questão (acerto e erro) e observar a posição de retorno. | O jogo retorna ao estado CENÁRIO com o personagem na posição imediatamente após o portal. | *Pendente* | *Pendente* |
| **RF13** — O jogo é vencido ao alcançar o castelo com ao menos uma vida. | RF | Concluir o percurso preservando pelo menos 1 vida. | A tela de vitória é exibida ao tocar o castelo. | *Pendente* | *Pendente* |
| **RF14** — O jogo termina em derrota quando as vidas chegam a zero. | RF | Provocar perdas sucessivas até zerar as vidas. | A partida é encerrada e a tela de derrota é exibida no momento em que as vidas chegam a 0. | *Pendente* | *Pendente* |
| **RF15** — O HUD deve exibir vidas restantes e feedback de acerto/erro. | RF | Observar o HUD durante toda uma partida, incluindo acertos e erros. | Vidas e mensagens de feedback são exibidas e atualizadas em tempo real. | *Pendente* | *Pendente* |
| **RF16** — O banco de perguntas deve fornecer questões sem repetição dentro de um mesmo nível. | RF | Jogar um nível completo e registrar as 3 questões sorteadas. | As 3 questões apresentadas são distintas entre si. | *Pendente* | *Pendente* |
| **RNF01** — *Usabilidade (ISO 25010: Operabilidade).* Os controles devem ser simples e aprendidos sem consulta a manual. | RNF | Sessão com 3 usuários sem instrução prévia, cronometrando o tempo até o primeiro salto bem-sucedido. | Todos os usuários realizam o primeiro salto em menos de 30 segundos. | *Pendente* | *Pendente* |
| **RNF02** — *Eficiência de Desempenho (ISO 25010: Comportamento temporal).* O jogo deve manter taxa de quadros estável. | RNF | Medir os FPS durante 3 minutos de jogo com contador ativo. | Taxa média ≥ 30 FPS, sem quedas perceptíveis de fluidez. | *Pendente* | *Pendente* |
| **RNF03** — *Portabilidade (ISO 25010: Adaptabilidade).* O jogo deve executar em computadores de configuração modesta. | RNF | Executar o jogo em ao menos duas máquinas distintas da equipe. | O jogo inicia e é jogável até o fim do nível em ambas as máquinas. | *Pendente* | *Pendente* |
| **RNF04** — *Manutenibilidade (ISO 25010: Modularidade).* O código deve ser modularizado por responsabilidade. | RNF | Inspeção de código verificando a separação entre cenário, física, portais, perguntas e vidas. | Cada responsabilidade reside em um módulo próprio, sem duplicação de lógica. | *Pendente* | *Pendente* |
| **RNF05** — *Usabilidade (ISO 25010: Estética da interface).* Cenário, obstáculos e portais devem ser visualmente distinguíveis. | RNF | Apresentar capturas de tela a 3 usuários e pedir que identifiquem cada elemento. | Todos identificam corretamente príncipe, obstáculos, portais e castelo. | *Pendente* | *Pendente* |
| **RNF06** — *Manutenibilidade (ISO 25010: Modificabilidade).* Novas perguntas devem ser adicionadas sem alterar a lógica do jogo. | RNF | Inserir uma nova questão no arquivo do banco de perguntas e reexecutar o jogo. | A nova questão passa a ser sorteável sem qualquer alteração no código-fonte. | *Pendente* | *Pendente* |
| **RNF07** — *Confiabilidade (ISO 25010: Tolerância a falhas).* Entradas inválidas na tela de perguntas não devem encerrar o jogo. | RNF | Pressionar teclas fora do conjunto "a"–"d" durante a exibição de uma questão. | As entradas são ignoradas, sem travamento e sem perda indevida de vida. | *Pendente* | *Pendente* |

*Tabela 1 - Requisitos e Testes Planejados*

## Regras de Negócio Associadas

- **RN01:** O jogador inicia a partida com 3 vidas.
- **RN02:** Cada nível possui exatamente 3 portais de perguntas.
- **RN03:** Cada portal abre exatamente uma pergunta de múltipla escolha.
- **RN04:** Uma resposta incorreta subtrai 1 vida.
- **RN05:** A colisão com um obstáculo (pedra ou árvore) subtrai 1 vida.
- **RN06:** A partida termina em derrota quando as vidas chegam a zero.
- **RN07:** A partida termina em vitória quando o príncipe alcança o castelo com ao menos
  1 vida restante.

## Evidências de Resultados

As evidências (capturas de tela do jogo em execução, registros de contagem de FPS e
fotografias das sessões de teste com usuários) serão inseridas nesta subseção a partir da
próxima entrega, numeradas sequencialmente a partir da *Figura 5*, conforme os testes da
Tabela 1 forem executados.
