# Cheaters FiveM — Central de downloads

Site Flask com catálogo público de links e painel administrativo protegido por senha.

## Render (plano gratuito)

- Runtime: Python
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
- Plano: Free
- Health check: `/health`

## Variáveis de ambiente

Configure em Render → serviço → Environment:

- `ADMIN_PASSWORD`: senha privada do painel (já configurada no serviço).
- `SECRET_KEY`: chave aleatória longa para assinar sessões.
- `GITHUB_TOKEN`: Fine-grained personal access token com acesso somente a este repositório e permissão **Contents: Read and write**.
- `GITHUB_REPOSITORY`: `orleasuarez-lab/cheaters-fivem-downloads`
- `GITHUB_BRANCH`: `main`
- `GITHUB_DATA_PATH`: `links.json`

Não coloque o token no código, no navegador ou em mensagens. Salve-o apenas como variável secreta no Render. Não compartilhe a senha do painel.

## Como funciona

- Visitantes veem os links publicados na página inicial e podem pesquisar por nome, descrição ou categoria.
- O administrador entra em `/admin`, adiciona links HTTPS, edita e exclui itens.
- Os arquivos ficam em serviços externos; este site guarda somente os links e as descrições.
- O catálogo é lido e atualizado pelo GitHub Contents API em `links.json`. Assim, os registros não dependem do disco temporário do Render.
- O token é usado somente no servidor e nunca é enviado ao navegador.

## Limites

O site e o serviço Render estão configurados no plano gratuito, sujeito aos limites e às políticas dos provedores. Os links apontam para serviços externos, que podem ter limites próprios, exigir login ou remover arquivos. Não há hospedagem de arquivos nem promessa de armazenamento ilimitado.

## Segurança

- Senha administrativa armazenada como variável de ambiente.
- Cookies HTTP-only, Secure e SameSite=Lax.
- Proteção CSRF nas operações administrativas.
- Bloqueio temporário após tentativas repetidas de senha.
- Apenas URLs HTTPS são aceitas para publicação.
