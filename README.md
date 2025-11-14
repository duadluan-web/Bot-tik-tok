# TikTok Bot — Complete Starter (Render)

Este projeto é um starter para rodar um bot que:
- recebe vídeos enviados por um app (Kodular etc)
- armazena os vídeos temporariamente
- publica via TikTok Content Posting API (quando integrado)

## Arquivos
- `main.py` : aplicação FastAPI principal
- `requirements.txt` : dependências
- `tokens.json` : criado em runtime para salvar tokens
- `videos/` : pasta onde uploads são salvos

## Como usar (Render)
1. Crie um repositório no GitHub e envie `main.py` e `requirements.txt`.
2. No Render, crie um "New Web Service" e conecte ao repositório.
3. Configure Environment Variables no painel do Render:
   - `CLIENT_KEY` : Client Key do TikTok
   - `CLIENT_SECRET` : Client Secret do TikTok
   - `REDIRECT_URI` : URL pública do seu serviço, ex: https://meubot.onrender.com/callback
   - (Opcional) `STORAGE_FILE` : caminho para o arquivo de tokens (default tokens.json)
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port 10000`

## Fluxo básico
- Usuário acessa `/login_tiktok` -> faz OAuth -> TikTok chama `/callback` -> token salvo
- App envia um POST `/upload_video` com o arquivo -> o servidor salva o arquivo e retorna o caminho
- App chama `/postar` com `video_path` retornado -> o servidor executa a lógica de upload para TikTok

## Atenção
- Os endpoints de upload/publish usados no exemplo são placeholders. Você deve consultar a docs oficial do TikTok Content Posting API e ajustar os endpoints e payloads para a sua app.
- Em produção, proteja endpoints com autenticação (API keys, JWT, etc).
