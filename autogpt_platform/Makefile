up:
	docker compose up -d;

down:
	docker compose down && docker system prune -f

reload-be:
	docker compose restart rest_server executor websocket_server;

reload-fe:
	docker compose build frontend && docker compose stop frontend && docker compose rm -f frontend && docker compose up -d frontend;