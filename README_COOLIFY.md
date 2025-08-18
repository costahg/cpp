# Deploy no Coolify (porta 3737)

## Pré-requisitos
- Repositório Git com: `extapi_core.py`, `extapi_http.py`, `extension_api.json`, `requirements.txt`, `Dockerfile`.
- Coolify conectado ao seu GitHub.

## Passo a passo (Dockerfile)
1) **Adicionar arquivos ao repo**
   - Copie estes arquivos para a raiz do seu repositório:
     - `extapi_core.py` (seu core)
     - `extapi_http.py` (HTTP)
     - `extension_api.json` (o JSON)
     - `requirements.txt`
     - `Dockerfile`
     - `.dockerignore` (opcional)

2) **Commit & push** no `main`.

3) **Coolify → New Resource → Application**
   - Provider: GitHub → escolha `costahg/cpp` (branch `main`).
   - Strategy: **Dockerfile**.
   - *Root Directory*: `/` (se os arquivos estão na raiz).

4) **Environment** (na aba *Environment variables*):
   - `EXTAPI_JSON=/app/extension_api.json`
   - `HOST=0.0.0.0`
   - `PORT=3737`

5) **Networking (Portas)**
   - Container Port: **3737**
   - Expose: HTTP (Traefik) habilitado.
   - Se usar domínio: adicione o domínio/subdomínio em *Domains* e ative HTTPS (Let's Encrypt).

6) **Deploy**
   - Clique **Deploy**. Aguarde status *running*.

7) **Testes**
   - `curl http://SEU_DOMINIO/health`  (se configurou domínio)
   - ou `curl http://IP_PUBLICO:3737/health` (sem domínio)
   - Endpoints úteis:
     - `/info`
     - `/methods/by-hash?hash=3863233950`
     - `/builtin/Color`
     - `/builtin/Color/layout?config=float_32`
     - `/builtin/Color/offset/a?config=float_32`
     - `POST /route` body: `{"q":"classe Node"}`

## Dica: atualizar o JSON sem redeploy
Se quiser trocar o `extension_api.json` sem redeploy:
- Na aba *Storage* do Coolify, crie um **Volume** (ex.: `extapi-data`) e **mapeie** `/data` no container.
- Coloque seu `extension_api.json` no volume (via *File Browser* do Coolify).
- Atualize `EXTAPI_JSON=/data/extension_api.json` nas env vars.
- O app recarrega o JSON quando o arquivo muda.

## Segurança básica
- CORS está liberado para testes. Em produção, limite `allow_origins` no `extapi_http.py` ao seu domínio.
- Se quiser proteger com token: use um proxy (Traefik/Middleware) ou adicione um `X-API-Key` simples no código.
