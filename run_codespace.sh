#!/usr/bin/env bash
# Builds and starts both SuperKart containers (run inside GitHub Codespaces)
set -e
docker rm -f backend frontend 2>/dev/null || true

# Step 1-2: build the images
docker build -t superkart-backend ./backend_files
docker build -t superkart-frontend ./frontend_files

# Step 3: create the network
docker network create superkart-net 2>/dev/null || true

# Step 4: backend on the network, published on port 7860
docker run -d --name backend --network superkart-net --network-alias backend -p 7860:7860 superkart-backend

# Step 5: frontend on the host network, calling the backend through its published port
docker run -d --name frontend --network host -e BACKEND_URL=http://localhost:7860 superkart-frontend

docker ps
echo "Backend on port 7860, frontend on port 8501 - set both ports to Public in the Ports tab."
