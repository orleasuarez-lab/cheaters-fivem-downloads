# Cheaters FiveM — Central de downloads

Aplicação Flask para publicar arquivos e disponibilizar downloads públicos.

## Render

- Runtime: Python
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
- Região recomendada: Ohio (mais próxima de São Paulo entre as regiões disponíveis)
- Configure as variáveis de ambiente descritas abaixo.

## Variáveis de ambiente

- `ADMIN_EMAIL`: e-mail administrativo autorizado.
- `SECRET_KEY`: chave aleatória longa e privada.
- `RESEND_API_KEY`: chave de API do Resend para enviar códigos de acesso.
- `MAIL_FROM`: remetente verificado no Resend, por exemplo `Cheaters FiveM <downloads@seudominio.com>`.
- `DATA_DIR`: `/var/data` quando o disco persistente estiver montado.
- `PERSISTENT_STORAGE`: mantenha `no` até conectar e testar um Render Disk em `/var/data`; depois altere para `yes`.
- `MAX_FILE_SIZE`: limite máximo por arquivo em bytes (padrão: 50 GiB).

## Armazenamento persistente

Anexe um Render Disk ao serviço com mount path `/var/data`. O app mantém o banco SQLite e os arquivos dentro de `DATA_DIR`. Os uploads ficam deliberadamente bloqueados enquanto `PERSISTENT_STORAGE=no`, para não dar a impressão de que os arquivos estão protegidos quando o disco ainda não está montado.

## Segurança

- Apenas `ADMIN_EMAIL` pode receber o código de acesso.
- Códigos expiram em 10 minutos e têm até 5 tentativas.
- Cookies de sessão são HTTP-only, Secure e SameSite=Lax.
- Upload em partes, fora da pasta pública; arquivos só são entregues pelo endpoint de download.
