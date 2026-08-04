# 2. Leitura Pré-Aula

As leituras abaixo fundamentam as decisões de requisitos e de arquitetura descritas nas
seções seguintes. Todas são de acesso aberto ou disponíveis via MinhaBiblioteca.

| Referência | Tipo | Relação com o projeto |
|------------|------|------------------------|
| ISO/IEC 25010 — *Systems and software Quality Requirements and Evaluation (SQuaRE)* | Norma técnica | Base para a classificação e redação dos requisitos não-funcionais (Seção 3). |
| NYSTROM, R. *Game Programming Patterns*. Disponível gratuitamente em `gameprogrammingpatterns.com` | Livro (acesso aberto) | Padrões **Game Loop**, **State** e **Update Method**, adotados na arquitetura (Seção 4). |
| SOMMERVILLE, I. *Engenharia de Software*. Pearson (MinhaBiblioteca) | Livro | Especificação de requisitos funcionais e não-funcionais e planejamento de testes. |
| Documentação oficial da engine/biblioteca 2D escolhida (tutoriais de introdução) | Tutorial | Renderização de sprites, laço principal e tratamento de entrada do teclado. |
| Documentação do Git e do GitHub — *Releases* e *Semantic Versioning* (`semver.org`) | Documentação | Organização do repositório, versionamento e publicação da primeira Release. |
| PRESSMAN, R. *Engenharia de Software: Uma Abordagem Profissional* (MinhaBiblioteca) | Livro | Método de engenharia e verificação/validação descritos na Seção 5. |

## Motivação do Projeto

> Esta subseção consolida e refina a motivação apresentada em relatórios anteriores.

### Contexto

Jogos digitais são uma das formas mais eficazes de engajamento e, quando combinados com
elementos educativos, tornam-se ferramentas de aprendizagem ativa. **Fuga para o Castelo**
nasce da intenção de unir a mecânica clássica de jogos de plataforma — divertida e
acessível — a desafios de conhecimentos gerais que estimulam o raciocínio do jogador.

### Problema

Jogos de plataforma tradicionais focam quase exclusivamente na habilidade motora (correr,
saltar, desviar), desperdiçando o potencial educativo do meio. Na direção oposta, jogos
puramente educativos frequentemente falham em manter o engajamento, por não oferecerem uma
experiência lúdica atraente. Falta equilíbrio entre diversão e aprendizado.

### Proposta

O projeto integra as duas dimensões em uma única experiência:

- A **jornada de plataforma** mantém o jogador imerso e ativo, exigindo reflexos para
  desviar de pedras e árvores no caminho até o castelo.
- Os **portais de conhecimento** introduzem pausas estratégicas nas quais o jogador
  responde a uma questão de múltipla escolha (alternativas de "a" a "d"), transformando o
  progresso no jogo em recompensa pelo acerto intelectual.

Como o erro tem consequência concreta na jogabilidade (perda de vida), cria-se um incentivo
natural para que o jogador raciocine antes de responder.

### Objetivos

**Objetivo geral:** desenvolver um jogo de plataforma 2D que combine desafios de destreza
com perguntas de conhecimentos gerais, promovendo diversão e aprendizado de forma integrada.

**Objetivos específicos:**

- Implementar a movimentação e o salto do personagem (o príncipe).
- Criar obstáculos (pedras e árvores) com detecção de colisão.
- Desenvolver o sistema de portais que transporta o jogador ao mundo de perguntas.
- Implementar um banco de perguntas de múltipla escolha com alternativas de "a" a "d".
- Gerenciar o sistema de vidas, penalizando colisões e respostas incorretas.
- Definir a condição de vitória: alcançar o castelo com ao menos uma vida.

### Público-Alvo

Estudantes e jogadores casuais de todas as idades que buscam uma experiência divertida e,
ao mesmo tempo, educativa.
