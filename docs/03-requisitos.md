# 3. Especificação de requisitos

## 3.1 Requisitos funcionais

| ID | Requisito |
|---|---|
| RF01 | O sistema deve executar o jogo no Raspberry Pi. |
| RF02 | O jogador deve movimentar o personagem e realizar saltos. |
| RF03 | O jogo deve apresentar obstáculos e detectar colisões. |
| RF04 | O jogo deve apresentar perguntas durante o percurso. |
| RF05 | Cada pergunta deve possuir de duas a quatro alternativas. |
| RF06 | O jogador deve responder usando teclado ou botões físicos. |
| RF07 | O sistema deve validar a resposta selecionada. |
| RF08 | O sistema deve fornecer retorno visual e sonoro para acertos e erros. |
| RF09 | Respostas corretas devem conceder moedas ou vantagens. |
| RF10 | Respostas incorretas devem apresentar uma explicação curta. |
| RF11 | O sistema deve contabilizar acertos, erros e sequência de acertos. |
| RF12 | O sistema deve medir o tempo de resposta de cada pergunta. |
| RF13 | O sistema deve evitar repetição imediata da mesma pergunta. |
| RF14 | As perguntas devem ser carregadas de arquivo externo. |
| RF15 | O sistema deve apresentar um resumo ao final da partida. |
| RF16 | Um servo deve representar fisicamente o progresso na fase. |
| RF17 | LEDs devem indicar acerto, erro, dano e vitória. |
| RF18 | Um buzzer deve produzir sons distintos para eventos relevantes. |
| RF19 | Um display externo deve apresentar pontuação ou informações da pergunta. |
| RF20 | O sistema deve possuir modo de diagnóstico de periféricos. |

## 3.2 Requisitos não funcionais

| ID | Categoria | Requisito |
|---|---|---|
| RNF01 | Desempenho | O jogo deve manter média mínima de 30 FPS em operação normal. |
| RNF02 | Latência | Entradas digitais devem ser reconhecidas em até 100 ms. |
| RNF03 | Aquisição | Botões devem ser amostrados com frequência mínima de 50 Hz. |
| RNF04 | Confiabilidade | Os botões devem possuir tratamento de debounce. |
| RNF05 | Concorrência | Leituras de sensores não devem bloquear a renderização. |
| RNF06 | Modularidade | A lógica do jogo deve ser independente dos drivers físicos. |
| RNF07 | Portabilidade | Deve existir modo teclado sem hardware conectado. |
| RNF08 | Observabilidade | FPS, CPU, memória e eventos devem ser registrados. |
| RNF09 | Robustez | A falha de um periférico secundário não deve encerrar o jogo. |
| RNF10 | Segurança | A pinagem deve respeitar os limites elétricos do Raspberry Pi. |
| RNF11 | Manutenção | Pinagem, montagem e dependências devem ser documentadas. |
| RNF12 | Encerramento | Atuadores devem retornar a estado seguro ao encerrar. |
| RNF13 | Usabilidade | Textos e comandos devem ser legíveis e adequados ao público infantil. |
| RNF14 | Extensibilidade | Novas perguntas devem poder ser adicionadas via JSON. |

## 3.3 Regras de recompensa

| Evento | Recompensa inicial |
|---|---|
| Resposta correta | 10 moedas |
| Resposta em até 5 segundos | 5 moedas adicionais |
| Três acertos consecutivos | Escudo contra uma colisão |
| Cinco acertos consecutivos | Uma vida extra |
| Resposta incorreta | Explicação e nenhuma perda de vida |
