# Atlas — Agente Editorial da Curadoria Prime

Agente em Python que cuida do ciclo editorial completo do site
[curadoriaprime.com](https://curadoriaprime.com). **Use pelo navegador**
(painel visual com botões e formulários) ou pelo terminal do VS Code.

## 🖥️ Usar SEM terminal (recomendado)

**Linux (Zorin OS):** dois cliques em **`abrir-painel.sh`** e escolha
*"Executar no terminal"* se perguntado. O navegador abre sozinho em
`http://127.0.0.1:5000` com o painel completo.

> **Primeira vez:** se o duplo clique abrir o arquivo num editor de texto,
> é porque falta a permissão de execução — faça uma vez só:
> botão direito no `.sh` → *Propriedades → Permissões* → marcar
> **"Permitir execução do arquivo como programa"**.

**Windows:** dois cliques em **`Abrir Painel Atlas.bat`**.

O painel tem todas as funções do agente:

- 🏠 **Início** — status da IA/WordPress e resumo do que já foi feito
- 🔎 **Analisar** — 1 clique varre o site; tabela com links quebrados e
  artigos desatualizados
- 📅 **Pautas** — botão "Gerar sugestões" + calendário editorial
- 📋 **Pesquisar** — campo para o nome do produto → ficha técnica
- ✍️ **Escrever** — escolhe a ficha, cola as notas das lojas, cola os links
  de afiliado e manda escrever
- ♻️ **Atualizar** — slug + motivo → versão atualizada do artigo
- 📄 **Artigos** — 👁️ pré-visualizar, ⬇️ baixar HTML e 🚀 enviar ao
  WordPress como rascunho

Cada tarefa roda em segundo plano com **log ao vivo** na tela (uma por vez).
No VS Code, dá para abrir o painel também por **F1 → Run Task →
"Atlas: abrir painel no navegador"**.

> Pré-requisito: instalação da seção 1 abaixo (feita uma única vez).

---

| Etapa | O que o Atlas faz |
|---|---|
| 🔎 **Analisar** | Lê todos os artigos do site, aponta **links quebrados** e detecta **artigos desatualizados** (ano antigo no título, sazonalidade que já passou, post sem update há muito tempo) |
| 📅 **Pautas** | Sugere novas pautas com IA e **programa um calendário editorial** em `dados/pautas/pautas.csv` |
| 📋 **Pesquisar** | Monta a **ficha técnica** completa do produto (specs, prós/contras, concorrentes, FAQ), opcionalmente enriquecida com busca na web |
| ✍️ **Escrever** | Gera o **artigo completo em HTML seguindo o padrão do site** (prova social, tabela de specs, veredito, fontes E-E-A-T...) |
| 🚀 **Publicar** | Envia/atualiza o artigo **no WordPress como rascunho** para você revisar e publicar |

---

## 1. Instalação (feita UMA vez)

### Linux (Zorin OS / Ubuntu / Debian) — jeito fácil ✅

Dois cliques em **`instalar-atlas.sh`** (escolha *"Executar no terminal"*).
Ele faz tudo sozinho: detecta o Python, cria o ambiente virtual, instala
as dependências e gera o arquivo `.env`. No final, pergunta se você quer
abrir o painel.

> Se reclamar que não conseguiu criar o ambiente virtual, falta um pacote
> do sistema — rode uma vez no terminal:
> `sudo apt update && sudo apt install python3-venv python3-pip`
> e depois execute o instalador de novo.

### Windows — jeito fácil ✅

Dois cliques em **`Instalar Atlas.bat`** (mesmas funções do instalador Linux).

### Manual (qualquer sistema)

No terminal do VS Code (`Ctrl + `` ` ``):

```bash
# 1) Crie o ambiente virtual
python3 -m venv .venv        # Windows: python -m venv .venv

# 2) Ative o ambiente
#    Linux/Mac:              source .venv/bin/activate
#    Windows (PowerShell):   .venv\Scripts\Activate.ps1

# 3) Instale as dependências
pip install -r requirements.txt

# 4) Crie seu arquivo de configuração
cp .env.example .env     # Windows: copy .env.example .env
```

## 2. Configurando a IA (escolha UMA opção)

### Opção A — Ollama (local e grátis) ✅ recomendada para começar

1. Instale o Ollama:
   - **Linux (Zorin):** `curl -fsSL https://ollama.com/install.sh | sh`
   - **Windows/Mac:** baixe em <https://ollama.com>
2. Baixe o modelo: `ollama pull llama3.1`
3. No `.env`, mantenha: `LLM_PROVIDER=ollama`

> Dica: modelos alternativos bons em português — `qwen2.5`, `gemma2`.

### Opção B — API paga (melhor qualidade de texto)

No `.env`, troque para `LLM_PROVIDER=openai` e preencha:

```env
LLM_API_KEY=sua-chave-aqui
LLM_BASE_URL=https://api.openai.com/v1      # veja outros no .env.example
LLM_MODEL=gpt-4o-mini
```

Funciona com OpenAI, **Groq** (rápido e com plano grátis),
**DeepSeek** (barato), Gemini e OpenRouter — basta trocar URL/modelo/chave.

## 3. Configurando o WordPress (só para publicar)

1. Painel WP → **Usuários → Perfil → Senhas de Aplicação**
2. Crie uma senha chamada `Atlas` e copie o código gerado
3. No `.env`:

```env
WP_USER=seu-usuario-wp
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

> O Atlas **nunca publica direto**: envia como **rascunho** (`draft`).

## 4. Usando

### Modo interativo (menu)

```bash
python atlas.py
```

### Fluxo completo típico

```bash
# 1. Verificar se IA e WordPress estão configurados
python atlas.py status

# 2. Varrer o site: links quebrados + artigos desatualizados
python atlas.py analisar

# 3. Pedir 8 sugestões de pauta já programadas no calendário
python atlas.py pautas --num 8
python atlas.py listar-pautas

# 4. Pesquisar um produto da pauta
python atlas.py pesquisar "Galaxy Buds FE"

# 5. Escrever o artigo (usa a ficha + pergunta seus links de afiliado)
python atlas.py escrever --ficha "galaxy buds fe" --pauta 3

#    ...com as notas reais das lojas que você copiou (ver seção abaixo):
python atlas.py escrever --ficha "galaxy buds fe" \
    --notas dados/pesquisas/notas_galaxy-buds-fe.txt

# 6. Revisar o HTML em dados/artigos/ e preencher pendências
#    (procure por {{LINK_, "X,X" e <!-- IMAGEM no arquivo)

# 7. Enviar ao WordPress como rascunho
python atlas.py publicar --slug galaxy-buds-fe-vale-a-pena

# 8. Atualizar um artigo já publicado que ficou desatualizado
python atlas.py atualizar --slug moto-g56-5g-review \
    --motivo "atualizar para 2026, novos preços e HyperOS 2" \
    --notas dados/pesquisas/notas_moto-g56-5g.txt
```

### ⭐ Notas das lojas via arquivo TXT

Para evitar números inventados no bloco "🏆 Aprovado por +X Compradores":

1. Copie `modelo/notas_lojas_exemplo.txt` para
   `dados/pesquisas/notas_<produto>.txt`
2. Preencha com os números reais das páginas da Amazon e do Mercado Livre
3. Pronto — o Atlas **detecta o arquivo automaticamente** na hora de
   escrever/atualizar (o nome precisa conter parte do nome do produto),
   ou entregue explicitamente com a flag `--notas`.

Sem o TXT, o redator deixa o placeholder `X,X` no HTML para você preencher.

## 5. Onde ficam os resultados

```
Atlas/
├── atlas.py               <- ponto de entrada (menu + comandos)
├── agente/                <- os 5 módulos do agente
├── modelo/
│   └── padrao_artigo.md   <- o "DNA" dos artigos do site (edite à vontade)
└── dados/
    ├── analises/          <- relatórios de links quebrados/desatualização
    ├── pautas/            <- calendário editorial (CSV + JSON)
    ├── pesquisas/         <- fichas técnicas dos produtos
    └── artigos/           <- HTML final + metadados SEO, prontos p/ revisão
```

## 6. Perguntas frequentes

**A IA inventou um dado de especificação. E agora?**
Sem chave de busca web (`TAVILY_API_KEY`), a ficha sai do conhecimento do
modelo. Sempre revise o JSON da ficha antes de escrever — e, para máxima
fidelidade, pegue uma chave grátis em <https://tavily.com>. Para as notas
das lojas, entregue o TXT com os números reais (seção acima).

**E o agendamento da publicação?**
Fica com você no WordPress: o Atlas entrega o post como **rascunho**,
você revisa e usa o agendador nativo do WP (Publicar → Agendar).

**Posso mudar o padrão dos artigos?**
Sim, tudo está em `modelo/padrao_artigo.md`. Edite as seções, emojis e
regras e o redator passa a seguir o novo modelo.

**O analisador derruba meu servidor?**
Não: o crawler faz 1 requisição por segundo e usa `HEAD` para testar links,
com pausas configuráveis em `agente/config.py`.
