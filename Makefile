.PHONY: dev prod

dev:
	uv run flask --app main run --debug --host :: --port 5000

# bump the amount of workers if you're handling a lot of traffic
prod:
	uv run gunicorn -w 4 --preload -b [::]:5000 main:app
