
HOW TO RUN THE PROJECT

run ollama and qdrant containers BEFORE agent


each agent change needs those comments to work:
    sudo docker-compose down
    sudo docker-compose build --no-cache
    sudo docker-compose up

if you made pull from git, it's best to do this for all containers:
    sudo docker-compose down
    sudo docker-compose build --no-cache
    sudo docker-compose up


in web search for:
dashboard: http://localhost:8004/
Qdrant: http://localhost:6333/dashboard#/collections
endpoint docs: http://localhost:8004/docs#/
Node-RED:http://localhost:1880/ (files for inport in the nodered/Procesy folder)


