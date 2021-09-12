
run:
	source ./dev/client.sh
	python3 abang/server.py

lint:
    flake8 ./abang
