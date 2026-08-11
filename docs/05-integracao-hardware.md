# 5. Plano de integração do hardware

## 5.1 Componentes previstos

| Componente | Aplicação |
|---|---|
| Joystick | Movimentação do personagem e menus |
| Quatro botões | Alternativas A, B, C e D |
| LED RGB | Verde para acerto e vermelho para erro |
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
O eixo X do joystick controla o movimento continuamente e o clique Z inicia o
jogo. Pulo e rolagem ficam exclusivamente nos botões azul e vermelho. As
respostas são emitidas apenas na borda de pressionamento, evitando múltiplas
respostas enquanto o botão fica segurado.

Pinagem inicial centralizada em `FreenovePinConfig`:

| Função | GPIO BCM |
|---|---:|
| Joystick Z (clique) | 7 |
| Joystick X / Y no ADS7830 | canais 5 / 6, I²C `0x48` |
| Vermelho — alternativa 1, rolar e reiniciar | 21 |
| Amarelo — alternativa 2 | 26 |
| Azul — alternativa 3 e pular | 20 |
| Verde — alternativa 4 | 16 |
| LED RGB vermelho / verde / azul | 17 / 24 / 12 |
| Buzzer passivo | 4 |

> Esta pinagem é uma proposta de software, não uma instrução definitiva de
> montagem. Antes de energizar o circuito, ela deve ser comparada ao modelo do
> Raspberry Pi, ao esquema do kit e ao tipo de LED RGB utilizado. Resistores e
> polaridades devem seguir o manual da Freenove.

Instalação prevista no Raspberry Pi OS:

```bash
sudo apt update
sudo apt install python3-gpiozero python3-smbus i2c-tools
sudo raspi-config
i2cdetect -y 1
pip install -r requirements-hardware.txt
CASTLE_HARDWARE=freenove python -m src.main
```

Em `raspi-config`, habilite `Interface Options → I2C`. O comando `i2cdetect`
deve mostrar o endereço `48`. O jogo aceita o `ADCDevice.py` oficial da
Freenove na raiz do repositório, mas também inclui um driver ADS7830 mínimo via
SMBus para funcionar sem essa cópia.

`python3-smbus` instalado pelo `apt` pode não ficar visível dentro de uma
`.venv`. Por isso, `requirements-hardware.txt` inclui `smbus2`, que oferece a
mesma API dentro do ambiente virtual.

Calibração opcional do joystick:

```bash
CASTLE_JOYSTICK_LOW=80 \
CASTLE_JOYSTICK_HIGH=175 \
CASTLE_JOYSTICK_INVERT_X=1 \
CASTLE_JOYSTICK_INVERT_Y=0 \
CASTLE_HARDWARE=freenove \
CASTLE_JOYSTICK_ENABLED=1 \
python -m src.main
```

O eixo X vem invertido por padrão para corresponder à orientação do módulo
Freenove. Se a montagem física estiver na orientação oposta, use
`CASTLE_JOYSTICK_INVERT_X=0`. A zona entre `LOW` e `HIGH` é neutra e evita
movimento involuntário quando a alavanca está solta.

Antes de abrir o jogo, confira os valores crus e o clique Z:

```bash
python -m src.hardware.joystick_diagnose
```

Em repouso, X e Y devem ficar entre os limites `LOW` e `HIGH`. Ao mover a
alavanca, um eixo deve se aproximar de 0 ou 255; ao clicar, Z deve mudar de 0
para 1.

Para desenvolvimento fora do Raspberry Pi, as fábricas dos dispositivos são
injetáveis. Assim, entradas, LEDs, buzzer, debounce lógico e encerramento podem
ser testados com objetos falsos, sem acessar pinos reais.

O joystick analógico já está integrado e é habilitado automaticamente no modo
`freenove`. Os próximos incrementos ficam isolados no mesmo adaptador: servo,
LCD e sensores. Eles não exigirão mudanças na física, nas fases ou no motor
educativo.
