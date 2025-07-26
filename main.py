import os
from validator import validate_all_files, print_error_report
from config import CUSTOM_ENTITIES, SUPPORTED_TAGS
import logging
import gc

def main():
    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='validator.log'
    )
    
    # Use relative path to Samples folder
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SAMPLES_FOLDER = os.path.join(BASE_DIR, "Samples")
    
    print(f"  Scanning folder: {SAMPLES_FOLDER}")
    print(f"  Files detected: {os.listdir(SAMPLES_FOLDER)}")

    try:
        # Process files one at a time with memory management
        results = {}
        for filename in os.listdir(SAMPLES_FOLDER):
          file_path = os.path.join(SAMPLES_FOLDER, filename)
          if os.path.isfile(file_path):  # Only process files, not directories
            try:
                print(f"\nProcessing {filename}...")
                file_results = validate_all_files(SAMPLES_FOLDER)
                results.update(file_results)
                gc.collect()
            except Exception as file_error:
               logging.error(f"Failed to process {filename}: {str(file_error)}")
               print(f"⚠ Error processing {filename}: {str(file_error)}")
               continue

        print_error_report(results)
        
    except Exception as e:
        error_msg = f"Critical error: {str(e)}"
        print(f"\n{error_msg}")
        logging.error(error_msg)
        print("Check if:")
        print("- Files exist in Samples/ folder")
        print("- Files are not corrupted or too large")

if __name__ == "__main__":
    main()