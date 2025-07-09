import os
import re
from collections import defaultdict
from parser import parse_xml, preprocess_file_content
from entity_checker import check_entities
from tag_checker import validate_tags
from config import CUSTOM_ENTITIES, SUPPORTED_TAGS, NON_CLOSING_TAGS

def validate_all_files(folder_path):
    results = {}

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.fnt', '.xml', '.txt')):
            file_path = os.path.join(folder_path, filename)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()

            # Enhanced Page Number Tracking
            page_numbers = {}
            current_page = "1"
            lines = raw_content.splitlines()
            
            for line_num, line in enumerate(lines, 1):
                # Handle both <Page X> and <P20> tags more robustly
                page_match = re.search(r'<Page\s+(\d+)\s*>', line, re.IGNORECASE)
                if page_match:
                    current_page = page_match.group(1)
                elif '<P20>' in line:
                    p20_match = re.search(r'<P20>(\d+)</P20>', line)
                    if p20_match:
                        current_page = p20_match.group(1)
                page_numbers[line_num] = current_page

            # Validation Pipeline
            cleaned_content = preprocess_file_content(raw_content)
            tree, parse_errors, _ = parse_xml(cleaned_content)
            categorized_errors = []

            # Process parse errors
            for error in parse_errors:
                if len(error) == 5:  # (category, line, col, msg, context)
                    cat, line, col, msg, context = error
                    page = page_numbers.get(line, "1")
                    categorized_errors.append((cat, line, page, msg, context))

            # Add entity validation errors (Repent or Reptab)
            entity_errors = check_entities(raw_content, CUSTOM_ENTITIES)
            for cat, line, col, msg in entity_errors:
                page = page_numbers.get(line, "1")
                context = lines[line-1].strip() if 0 < line <= len(lines) else "N/A"
                categorized_errors.append((cat, line, page, msg, context))

            # Add tag validation errors (Reptag)
            if tree is not None:
                tag_errors = validate_tags(tree, SUPPORTED_TAGS, NON_CLOSING_TAGS)
                for cat, line, col, msg in tag_errors:
                    page = page_numbers.get(line, "1")
                    context = lines[line-1].strip() if 0 < line <= len(lines) else "N/A"
                    categorized_errors.append((cat, line, page, msg, context))

            results[filename] = categorized_errors

    return results

def print_error_report(results):
    """Prints a formatted validation report matching the desired output"""
    print("\n--- SCAN SUMMARY ---")
    total_files = len(results)
    total_errors = sum(len(errs) for errs in results.values())
    clean_files = sum(1 for errs in results.values() if not errs)
    
    print(f"Files Scanned: {total_files}")
    print(f"Files with Errors: {total_files - clean_files}")
    print(f"Total Issues Found: {total_errors}\n")

    for filename, errors in results.items():
        if not errors:
            print(f"✔ {filename}: CLEAN\n")
            continue

        print(f"--- {filename}: {len(errors)} ISSUES ---\n")
        
        # Group by error type
        error_groups = defaultdict(list)
        for err in errors:
            error_groups[err[0]].append(err[1:])

        for category, err_list in error_groups.items():
            # Color coding
            color = {
                "Repent": "\033[91m",  # Red
                "Reptag": "\033[93m",  # Yellow
                "Reptab": "\033[94m",  # Blue
                "CheckSGM": "\033[96m" # Cyan
            }.get(category, "")
            reset = "\033[0m"

            print(f"{color}{category.upper()} ({len(err_list)}){reset}\n")
            
            for line, page, msg, context in err_list:
                print(f"Page {page}, Line {line}:")
                print(msg)
                print(f"Context: {context[:120]}{'...' if len(context) > 120 else ''}\n")

    print("--- VALIDATION COMPLETE ---\n")
