# 5. Plano de integração do hardware

## 5.1 Componentes previstos

| Componente | Aplicação |
|---|---|
| Joystick | Movimentação do personagem e menus |
| Quatro botões | Alternativas A, B, C e D |
| LED RGB | Verde para acerto, vermelho para erro e azul para bônus |
| Buzzer passivo | Efeitos de acerto, erro, dano e vitória |
| Servo motor | Indicador físico do progresso até o castelo |
| LCD | Pontuação, vidas, pergunta resumida ou estado |
| Potenciômetro | Ajuste de dificuldade ou volume |
| Fotoresistor | Alteração do cenário entre dia e noite |
| Sensor ultrassônico | Comando especial por aproximação |
| Matriz ou display | Vidas, moedas ou sequência de acertos |

## 5.2 Integração incremental

1. Validar o protótipo completo por teclado.
2. Substituir as alternativas 1 a 4 por quatro botões com debounce.
3. Integrar LED RGB e buzzer aos eventos de resposta.
4. Integrar servo ao progresso percentual da fase.
5. Integrar LCD à pontuação e ao estado atual.
6. Integrar joystick à movimentação.
7. Adicionar sensores analógicos e ambientais.
8. Executar todos os dispositivos simultaneamente e medir desempenho.

## 5.3 Estratégia de concorrência

O laço principal manterá a renderização e a lógica do jogo. Sensores de leitura lenta poderão operar em threads separadas, enviando eventos por uma fila segura. Atuadores serão atualizados apenas quando o estado mudar, evitando operações desnecessárias a cada quadro.
