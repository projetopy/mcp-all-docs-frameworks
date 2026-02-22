# MCP Server para Documentação de Frameworks (React, Vue, Django, etc.)

Este projeto implementa um servidor de contexto (no estilo MCP) usando **Django + DRF + ChromaDB + Sentence Transformers**. Ele permite que sua IA local (ex.: Continue.dev + qwen2.5-coder) consulte a documentação de qualquer framework ou biblioteca através de busca semântica (RAG). Basta clonar a documentação desejada e rodar a ingestão — o sistema é genérico e funciona com Markdown, MDX e outros formatos de texto.

## ✨ Funcionalidades

- Ingestão automática de documentação a partir de repositórios Git.
- Geração de embeddings com `sentence-transformers/all-MiniLM-L6-v2`.
- Armazenamento vetorial com ChromaDB (persistente).
- API REST simples para busca contextual.
- Fácil adaptação para React, Vue, Angular, Django, Laravel, etc.
- Integração direta com o **Continue.dev** no VS Code.

---

## 🧰 Pré-requisitos

- **Python 3.9+**
- **Git**
- **VS Code** com a extensão **Continue** instalada
- (Opcional) **Ollama** para rodar modelos locais (já configurado no seu `config.yaml`)

---

## 📦 Instalação do Servidor

1. **Clone este repositório** (ou crie seu próprio projeto a partir dos arquivos fornecidos):
   ```bash
   git clone https://github.com/projetopy/mcp-all-docs-frameworks
   cd mcp-all-docs-frameworks
   ```

2. **Crie e ative um ambiente virtual**:
   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux/macOS
   venv\Scripts\activate          # Windows
   ```

3. **Instale as dependências** (use o `requirements.txt` abaixo):
   ```bash
   pip install -r requirements.txt
   ```

   **Arquivo `requirements.txt`** (copie e cole):
   ```
   chromadb
   Django
   djangorestframework
   sentence-transformers
   langchain
   langchain-text-splitters
   ```

4. **Execute as migrações iniciais do Django**:
   ```bash
   python manage.py migrate
   ```

---

## 📥 Ingerindo a Documentação de um Framework

O processo é sempre o mesmo: clone a documentação desejada e execute o comando de ingestão apontando para a pasta.

### Exemplo 1: Documentação do React

```bash
git clone https://github.com/reactjs/react.dev.git
python manage.py ingest_docs --docs-path ./react.dev
```

### Exemplo 2: Documentação do Vue.js

```bash
git clone https://github.com/vuejs/docs.git vue-docs
python manage.py ingest_docs --docs-path ./vue-docs
```

### Exemplo 3: Documentação do Django (em reStructuredText)

Para projetos com documentação em `.rst`, você pode adaptar o script de ingestão (futuramente). Mas o mesmo processo funciona para arquivos `.md` e `.mdx`.

**Observação**: A primeira execução baixará o modelo de embeddings (`all-MiniLM-L6-v2`). Isso pode levar alguns minutos, mas é feito apenas uma vez.

---

## 🚀 Executando o Servidor

Com a documentação ingerida, inicie o servidor Django:

```bash
python manage.py runserver
```

A API estará disponível em:  
**`http://localhost:8000/api/search/`**

---

## 🔍 Testando a API

Você pode testar com `curl` ou qualquer cliente HTTP:

```bash
curl -X POST http://localhost:8000/api/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "useState", "k": 3}'
```

A resposta será um JSON contendo os trechos mais relevantes da documentação, com metadados (caminho do arquivo) e pontuação de distância.

---

## 🤖 Integração com o Continue.dev no VS Code

Agora vamos configurar o **Continue** para usar essa API como um provedor de contexto.

### 1. Localize o arquivo de configuração do Continue

No VS Code, abra o Continue e clique no ícone de engrenagem (ou acesse o arquivo diretamente em):
- **Linux/macOS**: `~/.continue/config.yaml #ou pela interface em Settings/Configs` 
	
- **Windows**: `%USERPROFILE%\.continue\config.yaml`

### 2. Adicione um `contextProvider` do tipo HTTP

Abra o arquivo `config.yaml` e adicione o seguinte bloco **após a lista de modelos** (respeitando a indentação YAML). Seu arquivo deve ficar parecido com este:

```yaml
name: Local Config
version: 1.0.0
schema: v1
models:
  - name: Llama 3.1 8B
    provider: ollama
    model: llama3.1:8b
    roles:
      - chat
      - edit
      - apply
  - name: Qwen2.5-Coder 1.5B
    provider: ollama
    model: qwen2.5-coder:1.5b-base
    roles:
      - autocomplete
  - name: Nomic Embed
    provider: ollama
    model: nomic-embed-text:latest
    roles:
      - embed
  - name: Autodetect
    provider: ollama
    model: AUTODETECT

# Adicione estas linhas:
contextProviders:
  - name: react-docs
    params:
      url: http://localhost:8000/api/search/
      title: React Docs
      description: Busca semântica na documentação do React
```

**Salve o arquivo.**

### 3. Como usar no chat do Continue

- No VS Code, abra o painel do Continue (Ctrl+Shift+P > "Continue: Open Chat").
- No chat, digite algo como:
  ```
  @react-docs como usar o hook useEffect?
  ```
- O Continue vai chamar sua API, obter os trechos mais relevantes e incluí-los como contexto para o modelo (que pode ser o `llama3.1:8b` ou o `qwen2.5-coder` que você configurou).

### 4. Opção alternativa: usando um script intermediário (caso prefira)

Se o provider HTTP não funcionar, você pode criar um script Python que chama a API e configurá-lo como um `contextProvider` do tipo `script`.

Crie o arquivo `/home/buids/react_mcp/mcp_client.py` (ajuste o caminho para o seu sistema):

```python
#!/usr/bin/env python3
import sys
import requests
import json

query = sys.argv[1]
response = requests.post("http://localhost:8000/api/search/", json={"query": query})
data = response.json()
for r in data["results"]:
    print(f"--- {r['metadata']['source']} ---")
    print(r['document'][:500] + "...\n")
```

Dê permissão de execução:
```bash
chmod +x /home/buids/react_mcp/mcp_client.py
```

Depois, no `config.yaml`, substitua o bloco `contextProviders` por:

```yaml
contextProviders:
  - name: react-docs-script
    params:
      command: python
      args:
        - /home/buids/react_mcp/mcp_client.py
        - $INPUT
```

---

## 🧠 Como Funciona (Arquitetura)

1. **Ingestão**:  
   - O script `ingest_docs.py` percorre todos os arquivos `.md`/`.mdx` da pasta fornecida.
   - Divide o conteúdo em chunks de ~800 tokens (com overlap de 200).
   - Gera embeddings para cada chunk usando `all-MiniLM-L6-v2`.
   - Armazena os vetores no ChromaDB (pasta `./chroma_db`), junto com metadados (caminho do arquivo).

2. **Busca**:  
   - Quando a IA faz uma pergunta, a API recebe a query, gera o embedding correspondente e consulta o ChromaDB.
   - Retorna os K chunks mais similares, com seus textos e metadados.

3. **Contexto para a IA**:  
   - O Continue insere esses trechos no prompt, permitindo que o modelo responda com informações atualizadas e precisas da documentação.

---

## 🌍 Usando com Outros Frameworks

Para trocar a documentação (ex.: de React para Vue), basta rodar a ingestão novamente apontando para o novo repositório. A coleção `react_docs` será substituída. Se quiser manter múltiplas coleções simultaneamente, você pode:

- Modificar o script de ingestão para aceitar um nome de coleção como parâmetro.
- Criar múltiplos endpoints na API (ex.: `/api/search/react/`, `/api/search/vue/`).

Caso precise de ajuda para expandir, consulte a seção **Personalizações** abaixo.

---

## 🔧 Personalizações Possíveis

- **Modelo de embedding**: Troque `all-MiniLM-L6-v2` por um modelo mais especializado (ex.: `intfloat/e5-small-v2`, `BAAI/bge-small-en`). Lembre-se de ajustar o tamanho dos vetores se necessário.
- **Tamanho dos chunks**: Altere `chunk_size` e `chunk_overlap` no script de ingestão para melhor precisão/desempenho.
- **Suporte a outros formatos**: Adapte o script para ler `.rst`, `.html` ou código-fonte. O LangChain possui splitters específicos (ex.: `RecursiveCharacterTextSplitter` para linguagens de programação).
- **Múltiplas coleções**: Modifique a view para aceitar um parâmetro opcional `collection` na requisição e busque na coleção correspondente.

---

## 🛠️ Troubleshooting

### Erro "You are using a deprecated configuration of Chroma"
**Solução**: Use `chromadb.PersistentClient(path="./chroma_db")` em vez da sintaxe antiga. O código já está corrigido nos arquivos fornecidos.

### A API retorna resultados vazios ou ruins
- Verifique se a ingestão foi concluída com sucesso (veja o total de chunks).
- Teste com uma query muito específica que existe na documentação.
- Aumente o `k` (número de resultados) na requisição.

### O Continue não encontra o provider `react-docs`
- Certifique-se de que o arquivo `config.yaml` está com a indentação correta (YAML é sensível a espaços).
- Reinicie o VS Code após salvar o arquivo.
- Verifique se o servidor Django está rodando (`python manage.py runserver`).

### O modelo não usa o contexto fornecido
- Alguns modelos podem ignorar contexto muito longo. Tente reduzir o número de chunks retornados (parâmetro `k`).
- No Continue, você pode forçar o uso do contexto digitando explicitamente `@react-docs` antes da pergunta.

---

## 📄 Arquivos do Projeto (Estrutura)

```
mcp-docs-server/
├── manage.py
├── config/               # pasta do projeto Django
│   ├── settings.py
│   ├── urls.py
│   └── ...
├── docs/                     # app principal
│   ├── management/
│   │   └── commands/
│   │       └── ingest_docs.py   # script de ingestão
│   ├── views.py                  # endpoint da API
│   └── urls.py
├── chroma_db/                # banco vetorial (criado na ingestão)
├── requirements.txt
└── README.md                 # este arquivo
```

---

## 📌 Conclusão

Agora você tem um **servidor de documentação inteligente** que pode alimentar sua IA local com contexto preciso de qualquer framework. Basta clonar a documentação desejada, rodar a ingestão e começar a usar no Continue.dev.

Se encontrar problemas ou quiser sugerir melhorias, sinta-se à vontade para abrir uma issue ou contribuir com o projeto.