FROM fsfe/pipenv:python-3.8

RUN apt-get update && apt-get install -y git

COPY ["main.py", "persistence.py", ".env", "/app/"]
WORKDIR /app
COPY ["Pipfile", "Pipfile.lock", "/app/"]
RUN pipenv install
CMD ["pipenv", "run", "python", "main.py"]
