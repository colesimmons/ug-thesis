import argparse
import os

from b2sdk.v2 import B2Api, InMemoryAccountInfo


def upload_directory_to_b2(
    local_dir, bucket_name, b2_application_key_id, b2_application_key
):
    # Set up Backblaze B2 credentials and API
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", b2_application_key_id, b2_application_key)

    # Get the bucket
    bucket = b2_api.get_bucket_by_name(bucket_name)

    # Retrieve all files currently in the bucket to avoid re-uploading existing files
    existing_files = set()
    for file_version, _ in bucket.ls():
        existing_files.add(file_version.file_name)

    # Upload files
    for root, dirs, files in os.walk(local_dir):
        for filename in files:
            local_file_path = os.path.join(root, filename)
            b2_file_path = os.path.relpath(
                local_file_path, start=local_dir
            )  # Maintains directory structure

            if b2_file_path not in existing_files:
                file_version = bucket.upload_local_file(
                    local_file=local_file_path, file_name=b2_file_path
                )
                print(
                    f"Uploaded {local_file_path} to {bucket_name} with file id {file_version.id_}"
                )
            else:
                print(f"Skipped {local_file_path}: already exists in the bucket.")


def main():
    # Create the parser
    parser = argparse.ArgumentParser(
        description="Upload files from a local directory to Backblaze B2 bucket, skipping existing files."
    )

    # Add the arguments
    parser.add_argument("local_dir", type=str, help="Local directory to upload")
    parser.add_argument("bucket_name", type=str, help="Backblaze B2 bucket name")
    parser.add_argument(
        "b2_application_key_id", type=str, help="Backblaze B2 application key ID"
    )
    parser.add_argument(
        "application_key", type=str, help="Backblaze B2 application key"
    )

    # Execute the parse_args() method
    args = parser.parse_args()

    upload_directory_to_b2(
        args.local_dir,
        args.bucket_name,
        args.b2_application_key_id,
        args.application_key,
    )


if __name__ == "__main__":
    main()
