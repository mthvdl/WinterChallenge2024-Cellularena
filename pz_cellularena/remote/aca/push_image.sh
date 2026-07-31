#!/usr/bin/env bash
# Builds the training image and pushes it to ACR.
# Must be run from the repo root (WinterChallenge2024-Cellularena/).
# Usage: ./pz_cellularena/remote/aca/push_image.sh -a <acr-name> -g <resource-group> [-t latest] [-e podman|docker]
set -euo pipefail

ACR_NAME=''
RESOURCE_GROUP=''
TAG='latest'
ENGINE='podman'

usage() {
    echo "Usage: $0 -a <acr-name> -g <resource-group> [-t <tag>] [-e podman|docker]"
    exit 1
}

while getopts 'a:g:t:e:h' opt; do
    case $opt in
        a) ACR_NAME=$OPTARG ;;
        g) RESOURCE_GROUP=$OPTARG ;;
        t) TAG=$OPTARG ;;
        e) ENGINE=$OPTARG ;;
        h) usage ;;
        *) usage ;;
    esac
done

[[ -z "$ACR_NAME" || -z "$RESOURCE_GROUP" ]] && usage
[[ "$ENGINE" != "podman" && "$ENGINE" != "docker" ]] && { echo "Engine must be podman or docker"; exit 1; }

ACR_SERVER=$(az acr show -n "$ACR_NAME" -g "$RESOURCE_GROUP" --query loginServer -o tsv | tr -d '\r')
IMAGE_FULL="${ACR_SERVER}/cellularena-train:${TAG}"

echo "Building $IMAGE_FULL from repo root with $ENGINE..."
echo "(Dockerfile: pz_cellularena/remote/aca/Dockerfile)"

# Build uses repo root as context so COPY pz_cellularena/ works
"$ENGINE" build -f pz_cellularena/remote/aca/Dockerfile -t "$IMAGE_FULL" .

echo ""
echo "Logging in to ACR..."
if [[ "$ENGINE" == "podman" ]]; then
    TOKEN=$(az acr login -n "$ACR_NAME" --expose-token --query accessToken -o tsv | tr -d '\r')
    "$ENGINE" login "$ACR_SERVER" \
        --username 00000000-0000-0000-0000-000000000000 \
        --password "$TOKEN"
else
    az acr login -n "$ACR_NAME"
fi

echo "Pushing $IMAGE_FULL..."
"$ENGINE" push "$IMAGE_FULL"

echo ""
echo "Image pushed: $IMAGE_FULL"
echo "Pass this image to run_job.sh with:  -i $IMAGE_FULL"
