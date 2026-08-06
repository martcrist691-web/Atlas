# PADRÃO DE ARTIGO — CURADORIA PRIME
# (Este arquivo é a referência que o redator usa para gerar o HTML final.
#  Foi extraído da análise de artigos reais publicados no site.)

## IDENTIDADE DO SITE
- Nome: Curadoria Prime
- Nicho: reviews e curadoria de tecnologia (smartphones, fones, notebooks,
  tablets, eletroportáteis) + guias de presentes sazonais.
- Tom: técnico mas acessível, direto, "sem ruído", primeiro nome plural
  ("analisamos", "testamos"), sempre com transparência sobre links de afiliado.
- Idioma: português do Brasil.
- Lojas de afiliado usadas: Amazon e Mercado Livre (links encurtados:
  https://link.amazon/XXXX e https://meli.la/XXXX — use os placeholders
  {{LINK_AMAZON}} e {{LINK_ML}} quando o usuário não informar o link real).

## ESTRUTURA OBRIGATÓRIA DO ARTIGO (nesta ordem)

1. **Selo do tipo de conteúdo** (linha única)
   Ex.: `📌 Review Completo — 2026` / `📌 Comparativo — Volta às Aulas 2026` /
   `🎁 Guia de Presentes — Dia dos Pais 2026`

2. **Parágrafo de abertura (resposta direta à busca)**
   - Cita o produto em **negrito** já na 1ª frase.
   - Resume 3-4 specs principais em negrito.
   - Informa faixa de preço em R$.
   - Termina com a promessa da análise ("Analisamos +X avaliações reais...").

3. **Nota geral** — linha: `⭐ Nota Geral: X.X/10` + selos (✅ 5G + NFC, Modelo 2025/2026 etc.)

4. **Bloco "📋 Metodologia deste review"**
   Explica a base da análise (specs oficiais do fabricante + testes de canais
   especializados + análise de avaliações reais na Amazon e Mercado Livre) e
   linka https://curadoriaprime.com/sobre-a-curadoria-prime/

5. **Bloco "🏆 Aprovado por +X Compradores"** (prova social)
   - Caixa Amazon: nota média (ex.: 4,6 de 5), nº de avaliações, % 5 estrelas,
     botão "🔗 Ver Preço Atual na Amazon".
   - Caixa Mercado Livre: nota média, nº de opiniões, distribuição de notas,
     "🤖 Resumo das Opiniões (IA do Mercado Livre)" com 1 citação,
     1 avaliação verificada em destaque, botão "🛒 Ver Preço Atual no Mercado Livre".
   - Fecho: "✅ Análise Confirmada por +X Compradores".

6. **📑 Índice de Conteúdo** — lista numerada de links âncora (#intro,
   #pros-cons, #specs, #design, ... #veredito). Os <h2> do artigo DEVEM ter
   os ids correspondentes.

7. **Seção 1 — `#intro`**: `<h2 id="intro">PRODUTO Vale a Pena? Análise Completa 2026</h2>`
   2-3 parágrafos de contexto + caixa "📣 Transparência" (divulgação de links
   de afiliado, linkando https://curadoriaprime.com/transparencia-curadoria-prime/)
   + sub-bloco "🛒 Onde Comprar: Melhores Preços de Hoje" com os 2 botões de loja.

8. **Seção 2 — `#pros-cons`**: `<h2 id="pros-cons">📊 Prós e Contras do PRODUTO</h2>`
   `<h3>✅ Pontos Positivos</h3>` com <ul> de 5-6 itens (cada um inicia com
   **característica em negrito:** explicação).
   `<h3>⚠️ Pontos de Atenção</h3>` com <ul> de 4-5 itens no mesmo formato.

9. **Seção 3 — `#specs`**: `<h2 id="specs">📋 Especificações Técnicas Completas</h2>`
   `<table>` de 2 colunas (Especificação | Detalhe) com 12-15 linhas:
   Processador, RAM, Armazenamento, Tela, Brilho, Câmera Traseira, Câmera
   Frontal, Bateria, Carregamento, Sistema, Conectividade, Resistência,
   Dimensões, Peso (adaptar ao tipo de produto).
   Fecha com parágrafo "**Destaque:** ..." sobre o diferencial na faixa de preço.

10. **Seções 4-8 — análise aprofundada** (uma <h2> com emoji por aspecto,
    adaptar ao produto): 🔨 Design e Construção, 🖥️ Tela, 📸 Câmera,
    🔋 Bateria e Carregamento, ⚡ Desempenho. Cada uma com 1-2 parágrafos +
    lista "✨ Destaques" ou "✓" de 3-4 itens quando couber.

11. **Seção 9 — `#comparativo`**: `<h2 id="comparativo">🆚 Comparativo Completo</h2>`
    Tabela comparando o produto com 2-3 concorrentes diretos (modelo, preço,
    3-4 specs chave, nota). Segue com recomendações condicionais:
    "→ Orçamento mais limitado? Escolha o X (link interno se existir)."

12. **Seção 10 — `#para-quem`**: `<h2 id="para-quem">✅ Para Quem É / ❌ Para Quem NÃO É</h2>`
    Duas listas de perfis ("Compre se você...", "Evite se você...").

13. **Seção 11 — `#faq`**: `<h2 id="faq">❓ Perguntas Frequentes</h2>`
    5-6 perguntas em <h3> com resposta curta em <p> (formato ideal para
    featured snippet do Google).

14. **Seção 12 — `#veredito`**: `<h2 id="veredito">🏁 Veredito Final: PRODUTO Vale a Pena?</h2>`
    Resposta direta em 1 frase + 2 parágrafos de justificativa com a nota
    repetida + para quem é a melhor escolha.

15. **Bloco final "🛒 Pronto para Comprar? Confira as Melhores Ofertas"**
    3 cartões: ⭐ Recomendado (o produto), 📱 alternativa premium,
    💰 alternativa barata — cada um com botões Amazon + Mercado Livre.
    Aviso: "**⚠️ Aviso:** Os preços mencionados são referentes à data de
    publicação e estão sujeitos a alteração..."

16. **"📚 Fontes Consultadas (E-E-A-T)"** — <ul> com 4-6 fontes: site oficial
    do fabricante, GSMArena (ou referência equivalente do nicho), páginas de
    avaliações da Amazon/Mercado Livre, canais especializados brasileiros
    (TechTudo, Adrenaline, Canaltech...).

17. **Fecho de engajamento** — 1 frase convidando a comentar o perfil de uso.

## REGRAS DE HTML (WordPress)
- Gerar APENAS o HTML do corpo do post (o que entra no editor de blocos do WP,
  como HTML personalizado). Sem <html>, <head> ou <body>.
- Tags permitidas: h2, h3, h4, p, ul, ol, li, table, thead, tbody, tr, th, td,
  strong, em, a, blockquote, hr, figure, img, figcaption, div.
- Todo <h2> de seção numerada no índice precisa de id="..." correspondente.
- Imagens: NÃO inventar URLs. Usar placeholder comentado:
  <!-- IMAGEM: descrição da foto necessária -->
- Links de afiliado: usar {{LINK_AMAZON}} e {{LINK_ML}} se o usuário não
  informou os links reais.
- Títulos otimizados para SEO: produto + "Vale a Pena em 2026?" + tipo de conteúdo.
- Preços sempre com "R$" e aproximados ("em torno de", "faixa de").
