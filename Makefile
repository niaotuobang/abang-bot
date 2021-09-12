
run:
	source ./dev/client.sh
	python3 abang/server_web.py

lint:
    flake8 ./abang
