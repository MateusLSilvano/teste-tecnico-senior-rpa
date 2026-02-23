# Como executar (local)

Este projeto expõe uma API (FastAPI) e um worker (RabbitMQ) para rodar crawls e persistir os resultados.

---

## Pré-requisitos

- **Docker Desktop** instalado e rodando
- **Docker Compose v2** (comando `docker compose`)
- (Opcional) **Python 3.10+** para rodar apenas os testes unitários fora do Docker

---

## Subir o ambiente com Docker Compose

Na raiz do repositório:

```bash
docker compose up -d --build
```

Para acompanhar logs:

```bash
docker compose logs -f api
docker compose logs -f worker
```

Para derrubar tudo:

```bash
docker compose down -v
```

> Dica: se você alterar código, rode `docker compose up -d --build` novamente para rebuildar as imagens.

---

## Acessar a API

Por padrão:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

---

## Executar o crawl (Hockey)

Criar um job:

```bash
curl -X POST http://localhost:8000/crawl/hockey
```

Listar jobs:

```bash
curl http://localhost:8000/jobs
```

Consultar um job específico (troque `<JOB_ID>`):

```bash
curl http://localhost:8000/jobs/<JOB_ID>
```

Buscar resultados do job:

```bash
curl http://localhost:8000/jobs/<JOB_ID>/results
```

---

## Executar o crawl (Oscar / AJAX)

Criar um job:

```bash
curl -X POST http://localhost:8000/crawl/oscar
```

Resultados:

```bash
curl http://localhost:8000/jobs/<JOB_ID>/results
```

---

## Rodar testes

### Testes unitários (rápido)

Com seu venv ativo:

```bash
python -m pytest -q app/tests/unit
```

### Testes de integração (usam containers)

Esses testes sobem Postgres e RabbitMQ via **testcontainers**, então você precisa do Docker Desktop rodando:

```bash
python -m pytest -q app/tests/integration
```

Ou tudo:

```bash
python -m pytest
```

---

## Troubleshooting rápido

### API/worker não sobe
Veja os logs:

```bash
docker compose logs -f
```

### Porta 8000 ocupada
Feche o processo que está usando a porta ou ajuste a porta no `docker-compose.yml`.

### RabbitMQ “not ready”
Pode acontecer nos primeiros segundos. Aguarde um pouco e verifique novamente os logs do worker:

```bash
docker compose logs -f worker
```
