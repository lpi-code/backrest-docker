#/usr/bin/env python3
import docker
import argparse
import json
import sys

def get_container_info(container_name):
    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
        container_info = {
            "name": container.name,
            "image": container.image.tags[0] if container.image.tags else container.image.id,
            "labels": container.labels,
            "volumes": container.attrs['Mounts'],
            "networks": container.attrs['NetworkSettings']['Networks'],
            "ports": container.attrs['NetworkSettings']['Ports'],
            "env": container.attrs['Config']['Env'],
            "command": container.attrs['Config']['Cmd'],
            "entrypoint": container.attrs['Config']['Entrypoint']
        }
        print(f"Collected container info for '{container_name}':")
        print(json.dumps(container_info, indent=2))
        return container_info
    except docker.errors.NotFound:
        print(f"Error: Container '{container_name}' not found.")
        sys.exit(1)

def pull_image(image_name):
    client = docker.from_env()
    try:
        print(f"Pulling image '{image_name}' from Docker Hub...")
        image = client.images.pull(image_name)
        print(f"Image '{image_name}' pulled successfully.")
        return image.tags[0] if image.tags else image.id
    except docker.errors.ImageNotFound:
        print(f"Error: Image '{image_name}' not found on Docker Hub.")
        sys.exit(1)
    except docker.errors.APIError as e:
        print(f"Error pulling image: {e}")
        sys.exit(1)


def restore_image_gzip(gzip_file):
    client = docker.from_env()
    try:
        print(f"Restoring Docker image from gzip-compressed tarball '{gzip_file}'...")
        image = client.images.load(open(gzip_file, 'rb'))
        print(f"Image restored successfully.")
        return image[0].tags[0] if image[0].tags else image.id
    except docker.errors.APIError as e:
        print(f"Error restoring image: {e}")
        sys.exit(1)

def recreate_container(container_info, new_image):
    client = docker.from_env()
    container_name = container_info['name']

    # Stop and remove the existing container
    try:
        container = client.containers.get(container_name)
        print(f"Stopping container '{container_name}'...")
        container.stop()
        # Check if container still exists
        try:
            container = client.containers.get(container_name)
            container.remove()
        except docker.errors.NotFound:
            pass
        print(f"Container '{container_name}' removed.")
    except docker.errors.NotFound:
        print(f"Container '{container_name}' does not exist or is already removed.")

    # Recreate the container with the new image and existing configuration
    print(f"Recreating container '{container_name}' with new image '{new_image}'...")
    try:
        client.containers.run(
            image=new_image,
            name=container_name,
            labels=container_info['labels'],
            volumes={v['Source']: {'bind': v['Destination'], 'mode': 'rw' if v['RW'] else 'ro'} for v in container_info['volumes']},
            ports={p.split('/')[0]: int(p_info[0]['HostPort']) for p, p_info in container_info['ports'].items() if p_info},
            environment=container_info['env'],
            command=container_info['command'],
            entrypoint=container_info['entrypoint'],
            detach=True,
            network=list(container_info['networks'].keys())[0]
        )
        print(f"Container '{container_name}' recreated successfully.")
    except Exception as e:
        print(f"Error recreating container: {e}")
        sys.exit(1)

def tag_image(image, new_tag):
    client = docker.from_env()
    try:
        print(f"Tagging image '{image}' with new tag '{new_tag}'...")
        client.images.get(image).tag(new_tag)
        print(f"Image '{image}' tagged with new tag '{new_tag}'.")
    except docker.errors.ImageNotFound:
        print(f"Error: Image '{image}' not found.")
        sys.exit(1)
    except docker.errors.APIError as e:
        print(f"Error tagging image: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Update a Docker container with a new image from Docker Hub.")
    parser.add_argument("container_name", help="Name of the running container to update.")
    parser.add_argument("new_image", help="New Docker image ID or tag to use for the container (e.g., 'nginx:latest' or 'ubuntu:20.04').")
    parser.add_argument("--gzip", help="Restore image from a gzip-compressed tarball", action="store_true")

    args = parser.parse_args()
    container_name = args.container_name
    new_image = args.new_image

    # Step 1: Get the container info
    container_info = get_container_info(container_name)

    # Step 2: Pull the new image
    if args.gzip:
        new_image = restore_image_gzip(new_image)
    else:
        new_image = pull_image(new_image)

    new_image_tag = f"restored_{new_image.split('@')[0]}"
    # Step 3: Tag the new image with the original image name
    tag_image(new_image, new_image_tag)
    # Step 4: Recreate the container with the new image
    recreate_container(container_info, new_image_tag)

if __name__ == "__main__":
    main()
