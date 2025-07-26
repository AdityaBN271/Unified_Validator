import os
import re
from collections import defaultdict
from parser import parse_xml, preprocess_file_content
from entity_checker import check_entities
from tag_checker import validate_tags, check_tag_nesting
from config import CUSTOM_ENTITIES, SUPPORTED_TAGS, NON_CLOSING_TAGS


def check_invalid_angle_tags(raw_content, allowed_tags):
    """
    Detects and flags unsupported angle-bracketed tags like <random>
    Skips valid dynamic and layout tags.
    """
    errors = []
    tag_pattern = re.compile(r'<\s*/?\s*([a-zA-Z0-9_]+)[^>]*>')

    layout_tags = {
        "P20", "Page", "CN", "HN02", "HN24", "P00", "B22", "HN68", "B24", "HN46",
        "B42", "P24", "P42", "B44", "B", "C5", "HN00", "HN20"
    }

    lines = raw_content.splitlines()
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(("<!--", "<?", "<!")):
            continue

        for match in tag_pattern.finditer(line):
            tag = match.group(1)
            tag_lower = tag.lower()

            is_dynamic = tag_lower.startswith("fnt") or tag_lower.startswith("fnr")

            if (
                tag in allowed_tags or
                tag in layout_tags or
                is_dynamic
            ):
                continue

            col = match.start() + 1
            errors.append((
                "Reptag", line_num, col, f"Unsupported tag <{tag}> found"
            ))

    return errors


def validate_all_files(folder_path):
    results = {}

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)

        # ✅ Accept all files, ignore folders
        if not os.path.isfile(file_path):
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()


        # Page tracking
        page_numbers = {}
        current_page = "1"
        lines = raw_content.splitlines()

        for line_num, line in enumerate(lines, 1):
            page_match = re.search(r'<Page\s+(\d+)\s*>', line, re.IGNORECASE)
            if page_match:
                current_page = page_match.group(1)
            elif '<P20>' in line:
                p20_match = re.search(r'<P20>(\d+)</P20>', line)
                if p20_match:
                    current_page = p20_match.group(1)
            page_numbers[line_num] = current_page

        categorized_errors = []

        # 🔍 Check for invalid tags BEFORE XML parse
        invalid_tag_errors = check_invalid_angle_tags(raw_content, SUPPORTED_TAGS)
        for cat, line, col, msg in invalid_tag_errors:
            page = page_numbers.get(line, "1")
            context = lines[line - 1].strip() if 0 < line <= len(lines) else "N/A"
            categorized_errors.append((cat, line, page, msg, context))

        # Parse
        cleaned_content = preprocess_file_content(raw_content)
        tree, parse_errors, _ = parse_xml(cleaned_content)

        for error in parse_errors:
            if len(error) == 5:
                cat, line, col, msg, context = error
                page = page_numbers.get(line, "1")
                categorized_errors.append((cat, line, page, msg, context))

        # Entity errors (Repent, Reptab)
        entity_errors = check_entities(raw_content, CUSTOM_ENTITIES)
        for cat, line, col, msg in entity_errors:
            page = page_numbers.get(line, "1")
            context = lines[line - 1].strip() if 0 < line <= len(lines) else "N/A"
            categorized_errors.append((cat, line, page, msg, context))

        # Nesting check
        nesting_errors = check_tag_nesting(raw_content)
        for cat, line, col, msg in nesting_errors:
            page = page_numbers.get(line, "1")
            context = lines[line - 1].strip() if 0 < line <= len(lines) else "N/A"
            categorized_errors.append((cat, line, page, msg, context))

        # Tag structure and validation rules
        if tree is not None:
            tag_errors = validate_tags(tree, SUPPORTED_TAGS, NON_CLOSING_TAGS)
            for cat, line, col, msg in tag_errors:
                page = page_numbers.get(line, "1")
                context = lines[line - 1].strip() if 0 < line <= len(lines) else "N/A"
                categorized_errors.append((cat, line, page, msg, context))

        # ✅ Deduplicate same errors (category, line, page, msg)
        unique_errors = set()
        deduped_errors = []

        for err in categorized_errors:
    # For tag errors, use a more general key to avoid duplicates
            if err[0].startswith("Reptag"):
               line = err[1]
               msg = err[3]
        # Create a general key for similar tag errors
               if "mismatch" in msg.lower() or "nest" in msg.lower():
                   dedup_key = ("Reptag", line, "tag_structure_issue")
               else:
                   dedup_key = (err[0], err[1], err[2], err[3])
            else:
               dedup_key = (err[0], err[1], err[2], err[3])
    
            if dedup_key not in unique_errors:
               unique_errors.add(dedup_key)
               deduped_errors.append(err)
        results[filename] = deduped_errors

    return results


def print_error_report(results):
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

        error_groups = defaultdict(list)
        for err in errors:
            error_groups[err[0]].append(err[1:])

        for category, err_list in error_groups.items():
            color = {
                "Repent": "\033[91m",
                "Reptag": "\033[93m",
                "Reptab": "\033[94m",
                "CheckSGM": "\033[96m"
            }.get(category, "")
            reset = "\033[0m"

            print(f"{color}{category.upper()} ({len(err_list)}){reset}\n")

            for line, page, msg, context in err_list:
                print(f"Page {page}, Line {line}:")
                print(msg)
                print(f"Context: {context[:120]}{'...' if len(context) > 120 else ''}\n")

    print("--- VALIDATION COMPLETE ---\n")
