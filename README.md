# Fuja para o Castelo

Jogo educativo infantil desenvolvido para a disciplina de Laboratório de Processadores. O sistema combina uma fase de plataforma em Pygame, perguntas de múltipla escolha e recompensas no jogo, com futura integração aos componentes do kit Freenove FNK0054 conectado a um Raspberry Pi.

## Integrantes

- Claudio Lucio Cunha da Silva
- Lays Vieira Zandomingos
- Solano Omar Oliveira do Nascimento

## Protótipo da Semana 1

O protótipo inicial possui:

- movimentação lateral e salto;
- obstáculos e detecção de colisão;
- portais educativos;
- perguntas de múltipla escolha;
- moedas, escudo, vidas e sequência de acertos;
- banco de perguntas em JSON;
- modo teclado para desenvolvimento sem hardware;
- interface de hardware preparada para integração posterior.

## Execução

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

No Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.main
```

## Controles

| Tecla | Ação |
|---|---|
| A/D ou setas | Movimentar |
| Espaço | Pular |
| S, seta para baixo ou Shift | Rolar |
| 1, 2, 3 e 4 | Responder perguntas |
| R | Reiniciar após derrota ou vitória |
| Esc | Sair |

## Documentação

- [Motivação](docs/01-motivacao.md)
- [Objetivos e escopo](docs/02-objetivos-escopo.md)
- [Requisitos](docs/03-requisitos.md)
- [Arquitetura](docs/04-arquitetura.md)
- [Plano de integração do hardware](docs/05-integracao-hardware.md)
- [Plano de testes](docs/06-plano-testes.md)
- [Cronograma](docs/07-cronograma.md)
