# Changelog

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/)
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [0.1.0] - 2026-07-28

Primeira entrega: planejamento, documentação inicial e organização do repositório.

### Adicionado
- Repositório GitHub público criado e organizado conforme as orientações gerais.
- Documentação inicial em Markdown, estruturada segundo o template de planejamento de
  relatório da disciplina:
  - Seção 1 — Identificação do Grupo.
  - Seção 2 — Leitura Pré-Aula, incluindo a motivação refinada do projeto.
  - Seção 3 — Especificação de Requisitos e Testes (16 RF e 7 RNF classificados pela
    ISO/IEC 25010, com testes planejados na Tabela 1).
  - Seção 4 — Arquitetura do Sistema, com diagrama de blocos, máquina de estados,
    diagrama de sequência e justificativa das decisões arquiteturais.
  - Seção 5 — Método Experimental, com método de engenharia, estratégia de verificação,
    procedimento de depuração e método de trabalho em grupo.
  - Seção 6 — Lições Aprendidas.
- Figuras 1 a 4 do relatório (`docs/img/`).
- PDF compilado dos arquivos Markdown para entrega no Moodle.
- README com visão geral, descrição do jogo, índice da documentação e estrutura do
  repositório.
- Licença MIT e arquivo `.gitignore`.

### Refinado em relação aos relatórios anteriores
- Motivação reescrita com problema, proposta, objetivo geral e objetivos específicos
  explícitos.
- Requisitos reescritos em formato testável, com valores concretos (3 vidas iniciais,
  3 portais por nível, decremento unitário por erro ou colisão).
- Requisitos não-funcionais classificados segundo as características da ISO/IEC 25010.
- Arquitetura detalhada em camadas, com rastreabilidade entre módulos e requisitos.
- Regras de negócio implícitas explicitadas (RN01 a RN07).
