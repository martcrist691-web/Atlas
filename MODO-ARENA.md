# Atlas no modo Arena — como trabalhar comigo pelo chat

Você pode usar o Atlas de dois jeitos: **na sua máquina** (painel/terminal,
quando quiser automatizar) ou **aqui no chat do Arena** (eu faço o trabalho
pesado e entrego pronto no repositório). Este arquivo documenta o modo Arena.

## O que EU faço aqui no Arena (basta pedir no chat)

| Você pede | O que eu entrego |
|---|---|
| **"analisar"** | Verifico links suspeitos do site um a um e devolvo diagnóstico dos quebrados reais vs. falsos positivos |
| **"pautas"** | Calendário editorial atualizado em `dados/pautas/pautas.csv` (commit no Git) |
| **"pesquisar \<produto\>"** | Ficha técnica com dados reais pesquisados na web em `dados/pesquisas/ficha_<produto>.json` |
| **"escrever \<pauta ou produto\>"** | Artigo completo em HTML no padrão do site em `dados/artigos/<slug>.html`, pronto para colar no WP como rascunho. **Me passe junto:** seus links de afiliado (Amazon/ML) e as notas das lojas (coladas ou em .txt) |
| **"atualizar \<artigo\>: \<o que mudar\>"** | Versão corrigida do artigo commitada para você republicar |
| **"imagem para \<artigo\>"** | Imagem de destaque gerada e salva no repositório |

Depois de cada entrega, na sua máquina: `git pull` na pasta do Atlas e
colar/publicar no WordPress (o agendamento continua manual, como combinamos).

## O que NÃO dá para fazer aqui (limites da sandbox)

- Crawl automático em massa (a sandbox não tem internet livre — eu verifico
  links por triagem, não os 291 de uma vez)
- Publicar direto no WordPress (não tenho suas credenciais — e você prefere
  agendar manualmente mesmo)
- Rodar o painel web de forma permanente

## Estado do projeto (atualizado em 06/08/2026)

**Análise do site:** 46 artigos, 291 links verificados. Diagnóstico:
- ~11 links **realmente quebrados**: posts internos que não existem
  (`apple-tv-4k`, `carregador-portatil-xiaomi-2`, `review-logitech-mk270`,
  `chromecast-google-tv-4k`, slug errado do IdeaPad 1, +5 no guia de câmeras)
  e 4 links de afiliado **falsos** no review do Redmi Note 15 Pro
  (`B0cxyz123`, `B0motoG85`, `meli.la/3abcDef`, `meli.la/4motoG85`)
- ~105 falsos positivos: sites que bloqueiam robôs (Amazon 503, fabricantes
  403) e encurtadores que recusam HEAD — **corrigido no código** (versão
  2f7d458 em diante classifica como "não verificável")
- 0 artigos desatualizados (site todo recente — julho/2026+)

**Calendário editorial:** 12 pautas em `dados/pautas/` (2 urgentes de
Dia dos Pais para 07/08, correções de links e 6 reviews novos).
