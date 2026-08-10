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

## 5.4 Camada de software preparada

O jogo seleciona a implementação por meio da variável `CASTLE_HARDWARE`:

- `keyboard` (padrão): funciona em computadores comuns e não importa GPIO Zero;
- `freenove`: instancia `FreenoveHardware` e acessa os GPIOs físicos.

O adaptador usa numeração **BCM**, botões com `pull_up=True` e debounce de 50 ms.
Movimento lateral é lido continuamente; salto e respostas são emitidos apenas
na borda de pressionamento, evitando múltiplos comandos enquanto o botão fica
segurado. LED RGB e buzzer já recebem o estado de saída abstrato do jogo.

Pinagem inicial centralizada em `FreenovePinConfig`:

| Função | GPIO BCM |
|---|---:|
| Esquerda / direita / salto | 17 / 27 / 22 |
| Respostas 1 a 4 | 5 / 6 / 13 / 19 |
| LED RGB vermelho / verde / azul | 16 / 20 / 21 |
| Buzzer | 26 |

> Esta pinagem é uma proposta de software, não uma instrução definitiva de
> montagem. Antes de energizar o circuito, ela deve ser comparada ao modelo do
> Raspberry Pi, ao esquema do kit e ao tipo de LED RGB utilizado. Resistores e
> polaridades devem seguir o manual da Freenove.

Instalação prevista no Raspberry Pi OS:

```bash
sudo apt update
sudo apt install python3-gpiozero
CASTLE_HARDWARE=freenove python -m src.main
```

Para desenvolvimento fora do Raspberry Pi, as fábricas dos dispositivos são
injetáveis. Assim, entradas, LEDs, buzzer, debounce lógico e encerramento podem
ser testados com objetos falsos, sem acessar pinos reais.

Os próximos incrementos ficam isolados no mesmo adaptador: joystick analógico
via ADC, servo, LCD e sensores. Eles não exigirão mudanças na física, nas fases
ou no motor educativo.
