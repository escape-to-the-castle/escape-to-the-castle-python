# 4. Arquitetura proposta

A arquitetura separa o jogo, o conteúdo educativo, o acesso ao hardware e o monitoramento. Essa separação permite executar o protótipo em um computador comum e, posteriormente, substituir o controle por teclado pelos dispositivos físicos sem modificar as regras principais.

```text
Entradas físicas ou teclado
          |
          v
Interface de hardware
- leitura de botões
- joystick
- debounce
- sensores
          |
          v
Controlador central
- estados
- eventos
- temporização
       /       \
      v         v
Motor do jogo  Motor educativo
- movimento    - perguntas
- colisões     - respostas
- fase         - recompensas
       \       /
          v
Gerenciador de saídas
- tela Pygame
- LEDs
- buzzer
- servo
- display
          |
          v
Monitoramento e logs
```

## 4.1 Módulos

- `src/main.py`: laço principal e integração dos módulos.
- `src/game/`: entidades, física, colisões e estado da partida.
- `src/education/`: carregamento e seleção de perguntas.
- `src/hardware/`: interface abstrata e implementação por teclado.
- `src/monitoring/`: coleta de FPS, CPU e memória.
- `data/questions.json`: banco externo de perguntas.

## 4.2 Estados principais

- `PLAYING`: personagem percorre a fase.
- `QUESTION`: jogo apresenta pergunta e aguarda resposta.
- `FEEDBACK`: acerto ou erro é apresentado por tempo limitado.
- `GAME_OVER`: vidas esgotadas.
- `VICTORY`: personagem alcança o castelo.
