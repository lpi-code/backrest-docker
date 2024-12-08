#/usr/bin/env python3
import argparse
import subprocess
import json
import os
import sys
import gzip
import shutil

def get_image_info(container_name):
    """Retrieve the image tag and image ID from a container name."""
    try:
        # Inspect the container to get the image details
        result = subprocess.run(
            ["docker", "inspect", container_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        # Parse the JSON output
        container_info = json.loads(result.stdout)[0]
        image_id = container_info["Image"]

        # Get the image name and tag
        image_name_result = subprocess.run(
            ["docker", "inspect", "-f", "{{.Config.Image}}", container_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        image_name_tag = image_name_result.stdout.strip()

        return image_name_tag, image_id

    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr.strip()}")
        sys.exit(1)

def save_image_info(container_name, output_file):
    """Save the image info to the specified file."""
    image_name_tag, image_id = get_image_info(container_name)
    image_info = f"{image_name_tag}@{image_id}"
    
    with open(output_file, "w") as f:
        f.write(image_info + "\n")

    print(f"Image info saved to {output_file}")

def save_image_gzip(container_name, gzip_file):
    """Save the Docker image as a gzip-compressed tarball."""
    try:
        image_name_tag, _ = get_image_info(container_name)
        
        # Export the image to a tar file first
        tar_file = gzip_file.replace(".tar.gz", ".tar")
        
        print(f"Saving Docker image to {tar_file}...")
        subprocess.run(
            ["docker", "save", "-o", tar_file, image_name_tag],
            check=True
        )

        # Compress the tar file to gzip
        with open(tar_file, 'rb') as f_in:
            with gzip.open(gzip_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        os.remove(tar_file)  # Remove the original tar file

        print(f"Docker image saved as gzip-compressed file: {gzip_file}")

    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr.strip()}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Save Docker container image info and optionally export the image as a gzip file.")
    parser.add_argument("container_name", help="Name of the Docker container")
    parser.add_argument("output_file", help="File to save the image info (format: image:tag@imageid)")
    parser.add_argument("--gzip", help="Save the Docker image as a gzip file", action="store_true")
    
    args = parser.parse_args()

    save_image_info(args.container_name, args.output_file)

    if args.gzip:
        gzip_file = os.path.splitext(args.output_file)[0] + ".tar.gz"
        save_image_gzip(args.container_name, gzip_file)

if __name__ == "__main__":
    main()
