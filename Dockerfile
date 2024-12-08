FROM garethgeorge/backrest:latest-alpine

# Install docker
RUN apk add --no-cache docker py-pip python3 && \
    mkdir -p /docker_scripts
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt --break-system-packages

# Copy the script
COPY docker_scripts /docker_scripts
RUN chmod +x /docker_scripts/*