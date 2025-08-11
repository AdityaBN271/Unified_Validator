import os
import sys
import logging
import gc
from validator import validate_all_files, print_error_report

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='validator.log'
    )

    # Get path from argument or input
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        input_path = input("Enter the file or folder path to validate: ").strip()

    # Clean up the path
    input_path = os.path.abspath(os.path.expanduser(input_path))

    # Check if path exists
    if not os.path.exists(input_path):
        print(f"❌ Error: '{input_path}' does not exist.")
        return

    try:
        # If it's a single file, validate only that file
        if os.path.isfile(input_path):
            folder = os.path.dirname(input_path)
            file_list = [os.path.basename(input_path)]
        # If it's a folder, validate all files in it
        elif os.path.isdir(input_path):
            folder = input_path
            file_list = os.listdir(folder)
        else:
            print(f"❌ Error: '{input_path}' is neither a file nor a folder.")
            return

        if not file_list:
            print("⚠ No files found to validate.")
            return

        print(f"📂 Scanning: {folder}")
        print(f"📄 Files detected: {file_list}")

        results = validate_all_files(folder, file_list)
        print_error_report(results)
        gc.collect()

    except Exception as e:
        error_msg = f"Critical error: {str(e)}"
        print(f"\n{error_msg}")
        logging.error(error_msg)

if __name__ == "__main__":
    main()
