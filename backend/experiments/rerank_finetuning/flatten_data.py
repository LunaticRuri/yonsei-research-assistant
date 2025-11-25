import os
import shutil
from pathlib import Path

def flatten_directory(source_dir, dest_dir):
    source_path = Path(source_dir)
    dest_path = Path(dest_dir)

    if not dest_path.exists():
        dest_path.mkdir(parents=True)
        print(f"Created destination directory: {dest_path}")

    moved_count = 0
    for root, dirs, files in os.walk(source_path):
        for file in files:
            if file.endswith('.json'):
                src_file = Path(root) / file
                dst_file = dest_path / file

                # Handle duplicates
                if dst_file.exists():
                    print(f"Warning: {file} already exists in destination. Renaming...")
                    base = dst_file.stem
                    suffix = dst_file.suffix
                    counter = 1
                    while dst_file.exists():
                        dst_file = dest_path / f"{base}_{counter}{suffix}"
                        counter += 1
                
                shutil.move(str(src_file), str(dst_file))
                moved_count += 1
                if moved_count % 100 == 0:
                    print(f"Moved {moved_count} files...")

    print(f"Finished moving {moved_count} files to {dest_path}")

if __name__ == "__main__":
    # Assuming the script is run from backend/experiments/rerank_finetuning/
    # and data is in ./data/raw_data
    
    # Adjust these paths if necessary based on where you run the script
    current_dir = Path(__file__).parent
    source_directory = current_dir / "data" / "raw_data"
    destination_directory = current_dir / "data" / "all_json_files"

    print(f"Source: {source_directory}")
    print(f"Destination: {destination_directory}")
    
    if not source_directory.exists():
        print(f"Error: Source directory {source_directory} does not exist.")
    else:
        flatten_directory(source_directory, destination_directory)
