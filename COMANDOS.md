# Comandos para incorporar o protótipo ao repositório

Execute na raiz do repositório `lab-proc`:

```bash
git checkout -b feat/prototipo-educativo-semana-1

mkdir -p projeto
cp -r /caminho/fuja-para-o-castelo-semana1/. projeto/
```

Crie o ambiente e teste:

```bash
cd projeto
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

No Raspberry Pi OS, caso a criação do ambiente virtual falhe por falta do módulo:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Depois do teste:

```bash
cd ..
git add projeto
git commit -m "feat: adiciona prototipo educativo e documentacao inicial"
git push -u origin feat/prototipo-educativo-semana-1
```

Após concluir o Pull Request:

```bash
git checkout main
git pull origin main
git tag -a v0.1.0 -m "Entrega da Semana 1"
git push origin v0.1.0
```

Na página do GitHub, crie uma Release a partir da tag `v0.1.0` e anexe o PDF consolidado.
