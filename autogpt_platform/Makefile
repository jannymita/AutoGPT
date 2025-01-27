up:
	docker compose up -d;

down:
	docker compose down && docker system prune -f

reload-be:
	docker compose restart rest_server executor websocket_server;

rebuild-be:
	docker compose build rest_server executor websocket_server;
	docker compose stop rest_server executor websocket_server;
	docker compose rm -f rest_server executor websocket_server;
	docker compose up -d rest_server executor websocket_server;

rebuild-fe:
	docker compose build frontend && docker compose stop frontend && docker compose rm -f frontend && docker compose up -d frontend;