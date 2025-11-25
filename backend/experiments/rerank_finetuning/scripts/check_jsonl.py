import json
import argparse
import sys
from collections import deque

def check_jsonl(file_path, num_lines=5):
    """
    Reads the last num_lines of a JSONL file and prints them.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            buffer = deque(maxlen=num_lines)
            total_lines = 0
            for line in f:
                total_lines += 1
                buffer.append((total_lines, line))
            
            for line_num, line in buffer:
                try:
                    data = json.loads(line)
                    print(f"--- Line {line_num} ---")
                    print(json.dumps(data, indent=4, ensure_ascii=False))
                except json.JSONDecodeError as e:
                    print(f"--- Line {line_num} (Error decoding JSON) ---")
                    print(f"Error: {e}")
                    print(f"Content: {line.strip()}")
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check the last few lines of a JSONL file.")
    parser.add_argument("file_path", help="Path to the JSONL file")
    parser.add_argument("-n", "--lines", type=int, default=5, help="Number of lines to read (default: 5)")

    args = parser.parse_args()

    check_jsonl(args.file_path, args.lines)
