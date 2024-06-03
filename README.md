<<<<<<< HEAD
# projai

Pacote para criação de projetos de pesquisa

## Installação

1. Baixe este repositório e extraia seus arquivos (ou clone).
2. instale o pacote poetry:

```bash
pip install poetry
```

3. Na pasta do pacote, crie um ambiente de desenvolvimento do Python:

```bash
python -m venv .venv
```

3. Carrege o ambiente:

- **Linux**:

```bash
source .venv/bin/activate
```

- **Windows**:

Antes de ativar o ambiente de desenvolvimento, execute o seguinte comando:

```shell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser -Force
```

4. Então ative o ambiente:

```shell
.\.venv\Scripts\Activate.ps1
```

5. E finalmente, instale o pacote `projai`:

```bash
poetry install
```

## Uso

Este pacote usa a api da Openai. Então, pege sua chave api, inclua num arquivo `.env`, assim como está no modelo `.sample.env`.

## App Projeto Inovafit

Exemplo rodando em ambiente Jupyter:

```python
from projai import AppProjectInovafit

config = {
    "knowledge_area": "Tecnologia",
    "area": "Tecnologia de informação e comunicação",
    "subject": "Inteligência artificial",
    "topic": "Modelos de linguagem aplicados ao ensino de física",
}

app = AppProjectInovafit(**config)
await app.run()
```

Exemplo rodando em script:

```python
from projai import app_project_inovafit

config = {
    "knowledge_area": "Ciências da Terra",
    "area": "Física",
    "subject": "Física Computacional",
    "topic": "Modelos de linguagem aplicados a soluções de equações diferenciais não lineares",
}
app_project_inovafit(**config)
```
=======
# geradoria
Gerador de documentos
>>>>>>> 1d5d65a4c5d1e23c1661d6bcbf634928b5afb738
