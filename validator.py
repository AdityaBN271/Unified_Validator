import os
import re
from collections import defaultdict
from parser import parse_xml, preprocess_file_content
from entity_checker import check_entities
from tag_checker import validate_tags, check_tag_nesting, check_cross_page_tags
from config import CUSTOM_ENTITIES, SUPPORTED_TAGS, NON_CLOSING_TAGS


def is_valid_layout_tag(tag):
    match = re.match(r'^(P|B|HN)(\d{1,2})(?:,(\d{1,2}))?$', tag)
    if not match:
        return False

    prefix, first, second = match.group(1), match.group(2), match.group(3)

    try:
        if second is not None:
            first_val = int(first)
            second_val = int(second)
        else:
            if len(first) == 2:
                first_val = int(first[0])
                second_val = int(first[1])
            else:
                first_val = int(first)
                second_val = None
    except ValueError:
        return False

    is_valid = lambda x: x in range(2, 21, 2)

    if not is_valid(first_val):
        return False
    if second_val is not None and not is_valid(second_val):
        return False
    if second_val is not None and (first_val >= 10 or second_val >= 10) and second is None:
        return False

    return True


def check_invalid_angle_tags(raw_content, allowed_tags):
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
                is_dynamic or
                is_valid_layout_tag(tag)
            ):
                continue

            col = match.start() + 1
            errors.append(("Reptag", line_num, col, f"Unsupported tag <{tag}> found"))

    return errors


def check_blank_lines_after_page_one(raw_content):
    """
    Reports error if there are two blank lines after <Page 1> with no tag following.
    """
    errors = []
    lines = raw_content.splitlines()

    page_one_pattern = re.compile(r'<\s*Page\s+1\s*>', re.IGNORECASE)

    for i, line in enumerate(lines):
        if page_one_pattern.search(line):
            if i + 2 < len(lines):
                if lines[i + 1].strip() == "" and lines[i + 2].strip() == "":
                    if i + 3 < len(lines):
                        next_line = lines[i + 3].strip()
                        # No tag like <...> or [...] or {...}
                        if not re.match(r'[\[<{]', next_line):
                            errors.append((
                                "CheckSGM",
                                i + 2,  # report the second blank line number
                                1,
                                "No tag found after two consecutive blank lines following <Page 1>"
                            ))
            break
    return errors


def validate_all_files(folder_path, files_to_check=None):
    results = {}

    # If no file list provided, read all from folder
    if files_to_check is None:
        files_to_check = os.listdir(folder_path)

    for filename in files_to_check:
        file_path = os.path.join(folder_path, filename)

        if not os.path.isfile(file_path):
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        # Track page numbers
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

        # New blank-line check after <Page 1>
        blank_line_errors = check_blank_lines_after_page_one(raw_content)
        for cat, line, col, msg in blank_line_errors:
            page = page_numbers.get(line, "1")
            context = lines[line - 1].strip() if 0 < line <= len(lines) else "N/A"
            categorized_errors.append((cat, line, page, msg, context))

        # Remove SPage tags and check invalid tags
        raw_content = re.sub(r"<\s*SPage\b[^>]*>", "", raw_content, flags=re.IGNORECASE)
        invalid_tag_errors = check_invalid_angle_tags(raw_content, SUPPORTED_TAGS)
        for cat, line, col, msg in invalid_tag_errors:
            page = page_numbers.get(line, "1")
            context = lines[line - 1].strip() if 0 < line <= len(lines) else "N/A"
            categorized_errors.append((cat, line, page, msg, context))

        # Parse XML
        cleaned_content = preprocess_file_content(raw_content)
        tree, parse_errors, _ = parse_xml(cleaned_content)
        for error in parse_errors:
            if len(error) == 5:
                cat, line, col, msg, context = error
                page = page_numbers.get(line, "1")
                categorized_errors.append((cat, line, page, msg, context))

        # Entities
        entity_errors = check_entities(raw_content, CUSTOM_ENTITIES)
        for cat, line, col, msg in entity_errors:
            page = page_numbers.get(line, "1")
            context = lines[line - 1].strip() if 0 < line <= len(lines) else "N/A"
            categorized_errors.append((cat, line, page, msg, context))

        # Nesting
        nesting_errors = check_tag_nesting(raw_content)
        for cat, line, col, msg in nesting_errors:
            page = page_numbers.get(line, "1")
            context = lines[line - 1].strip() if 0 < line <= len(lines) else "N/A"
            categorized_errors.append((cat, line, page, msg, context))

        # Cross-page tags
        cross_page_errors = check_cross_page_tags(raw_content)
        for cat, line, col, msg in cross_page_errors:
            page = page_numbers.get(line, "1")
            context = lines[line - 1].strip() if 0 < line <= len(lines) else "N/A"
            categorized_errors.append((cat, line, page, msg, context))

        # Tag structure
        if tree is not None:
            tag_errors = validate_tags(tree, SUPPORTED_TAGS, NON_CLOSING_TAGS)
            for cat, line, col, msg in tag_errors:
                page = page_numbers.get(line, "1")
                context = lines[line - 1].strip() if 0 < line <= len(lines) else "N/A"
                categorized_errors.append((cat, line, page, msg, context))

        # Deduplicate
        unique_errors = set()
        deduped_errors = []
        for err in categorized_errors:
            if err[0].startswith("Reptag"):
                line = err[1]
                msg = err[3]
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
