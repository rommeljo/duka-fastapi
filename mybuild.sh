# an sh file is an executable file in linux/ubuntu
git pull 
docker-compose down
docker-compose up --build -d
docker logs -f fastapi