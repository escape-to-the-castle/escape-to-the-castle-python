# 6. Plano de testes

## 6.1 Testes funcionais

- Verificar movimentação, salto e limites da tela.
- Verificar colisão com obstáculos.
- Verificar abertura de perguntas nos portais.
- Verificar seleção das quatro alternativas.
- Verificar moedas, escudo, vidas e sequências.
- Verificar vitória, derrota e reinício.
- Verificar carregamento e validação do JSON.

## 6.2 Testes de hardware

Cada componente deverá possuir um programa isolado de diagnóstico antes da integração. Os testes devem confirmar pinagem, sentido lógico, debounce, tempo de resposta e estado seguro de encerramento.

## 6.3 Testes de desempenho

| Cenário | Configuração |
|---|---|
| Referência | Apenas jogo e teclado |
| Carga baixa | Botões e LEDs |
| Carga média | Botões, LEDs, buzzer, servo e LCD |
| Carga alta | Todos os periféricos e sensores |
| Sobrecarga | Todos os periféricos, logs detalhados e carga gráfica ampliada |

Métricas: FPS médio e mínimo, CPU, memória, latência média e máxima, tempo de leitura dos sensores, eventos perdidos e variação temporal dos atuadores.
