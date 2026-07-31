FROM dockerhub.rnd.amadeus.net/registry-1-docker-io-remote/nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && ln -s /usr/bin/python3 /usr/local/bin/python \
    && rm -rf /var/lib/apt/lists/*

# --trusted-host bypasses corporate TLS-inspection proxy for pip downloads
RUN pip3 install --no-cache-dir \
        --trusted-host pypi.org \
        --trusted-host files.pythonhosted.org \
        --trusted-host download.pytorch.org \
        --trusted-host download-r2.pytorch.org \
        torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Install remaining deps from requirements.txt (mirrors environment.yml, excludes torch).
COPY pz_cellularena/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir \
        --trusted-host pypi.org \
        --trusted-host files.pythonhosted.org \
        -r /tmp/requirements.txt

COPY pz_cellularena/ /app/pz_cellularena/

WORKDIR /app/pz_cellularena
ENTRYPOINT ["python"]
