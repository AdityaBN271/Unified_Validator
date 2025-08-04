from lxml import etree
from entity_checker import check_entities
from config import SUPPORTED_TAGS, NON_CLOSING_TAGS, TAG_RELATIONSHIPS, BALANCED_TAGS,INVALID_NESTING_RULES
from lxml.etree import _Element
import logging
import re

logger = logging.getLogger(__name__)

def is_valid_layout_tag(tag):
    """
    Validates layout tags like P24, B10, HN2, P2, P2,10, B10,12, etc.
    Rules:
    - Tag starts with P, B, or HN
    - Contains 1 or 2 numbers, each must be multiple of 2 (2–20)
    - If either number is two-digit, comma is required
    - If single combined (e.g., P24), split into digits
    """
    match = re.match(r'^(P|B|HN)(\d{1,2})(?:,(\d{1,2}))?$', tag)
    if not match:
        return False

    prefix, first, second = match.group(1), match.group(2), match.group(3)

    try:
        # If comma present
        if second is not None:
            first_val = int(first)
            second_val = int(second)
        else:
            # If only one number present
            if len(first) == 2:
                first_val = int(first[0])
                second_val = int(first[1])
            else:
                first_val = int(first)
                second_val = None
    except ValueError:
        return False

    # Helper: check if number is valid multiple of 2 up to 20
    is_valid = lambda x: x in range(2, 21, 2)

    if not is_valid(first_val):
        return False

    if second_val is not None and not is_valid(second_val):
        return False

    # If either value is two-digit, comma must be present
    if second_val is not None and (first_val >= 10 or second_val >= 10) and second is None:
        return False

    return True



def validate_tags(tree, allowed_tags=None, non_closing_tags=None, line_mapping=None):
    errors = []
    if tree is None:
        return errors

    root = tree.getroot()

    def is_fnt_variant(tag):
        tag_lower = tag.lower()
        return (tag_lower.startswith('fnt') and 
                (tag_lower in {'fnt', 'fnt*'} or 
                 tag_lower[3:].isdigit()))

    def is_non_closing(tag):
        tag_lower = tag.lower()
        non_closing_tags_lower = {t.lower() for t in (non_closing_tags or NON_CLOSING_TAGS)}
        return any(
            tag_lower == base_tag.lower() or
            (base_tag.endswith('*') and tag_lower.startswith(base_tag.rstrip('*').lower())) or
            (base_tag[:-1].isdigit() and tag_lower == base_tag.lower()[:-1])
            for base_tag in non_closing_tags_lower
        )

    for elem in root.iter():
        tag = elem.tag
        parent = elem.getparent()
        parent_tag = parent.tag if parent is not None else None

        line = elem.sourceline or 0
        col = getattr(elem, "sourcepos", 0)
        orig_line = line_mapping.get(line, line) if line_mapping else line

        if allowed_tags and tag not in allowed_tags and not is_valid_layout_tag(tag):

            errors.append((
                "Reptag",
                orig_line,
                col,
                f"Unsupported tag <{tag}> found"
            ))

        if is_fnt_variant(tag) and parent_tag != 'FN':
            errors.append((
                "Reptag",
                orig_line,
                col,
                f"<{tag}> must be inside <FN> tags (found outside)"
            ))

        if is_fnt_variant(tag) and elem.tail and '</' + tag.lower() + '>' in elem.tail.lower():
            errors.append((
                "Reptag",
                orig_line,
                col,
                f"<{tag}> is a non-closing tag (do not use </{tag}>)"
            ))

        if parent_tag == 'FN' and not is_fnt_variant(tag) and tag.lower() != 'fn':
            errors.append((
                "Reptag",
                orig_line,
                col,
                f"Only <fnt*> tags allowed inside <FN>, found <{tag}>"
            ))

        # Custom rule: EMB/EMS/EMU must not contain EM, EMB, EMS, or EMU
        if parent_tag in INVALID_NESTING_RULES and tag in INVALID_NESTING_RULES[parent_tag]:
            errors.append((
                "Reptag",
                orig_line,
                col,
                f"Invalid nesting: <{tag}> should not be inside <{parent_tag}>"
            ))

    fn_stack = []
    for event, elem in etree.iterwalk(tree, events=("start", "end")):
        tag = elem.tag
        line = elem.sourceline or 0
        col = getattr(elem, "sourcepos", 0)
        orig_line = line_mapping.get(line, line) if line_mapping else line

        if event == "start":
            if tag == 'FN':
                fn_stack.append((elem, orig_line, col))
        elif event == "end":
            if tag == 'FN' and fn_stack:
                fn_elem, fn_line, fn_col = fn_stack.pop()
                if any(not is_fnt_variant(child.tag) for child in fn_elem):
                    errors.append((
                        "Reptag",
                        orig_line,
                        col,
                        f"<FN> contains invalid child elements"
                    ))

    return errors




def check_tag_balancing(file_content):
    """
    Improved tag balancing checker that:
    1. Properly tracks opening/closing tags
    2. Handles self-closing tags
    3. Avoids duplicate error reporting
    4. Provides accurate line/column positions
    """
    stack = []
    errors = []
    lines = file_content.splitlines()
    
    # Match tags, including self-closing and ignoring attributes
    tag_pattern = re.compile(r'<(/?)([A-Za-z][A-Za-z0-9]*)(?:\s+[^>]*?)?(/?)\s*>')
    
    for line_num, line in enumerate(lines, 1):
        for match in tag_pattern.finditer(line):
            is_closing = bool(match.group(1))  # True if </tag>
            is_self_closing = bool(match.group(3))  # True if <tag/>
            tag_name = match.group(2).upper()
            col = match.start() + 1  # 1-based column position
            
            # Skip non-balanced tags and self-closing tags
            if tag_name not in BALANCED_TAGS or is_self_closing:
                continue
                
            if not is_closing:
                # Opening tag - push to stack
                stack.append((tag_name, line_num, col))
            else:
                # Closing tag - check balance
                if not stack:
                    errors.append((
                        "Reptag-balance",
                        line_num,
                        col,
                        f"Unexpected closing tag </{tag_name}> with no opening tag",
                        line.strip()
                    ))
                else:
                    last_tag, last_line, last_col = stack[-1]
                    if last_tag == tag_name:
                        stack.pop()  # Properly matched
                    else:
                        # Mismatch - report error
                        errors.append((
                            "Reptag-balance",
                            last_line,
                            last_col,
                            f"Unclosed tag <{last_tag}> expected matching </{last_tag}> before </{tag_name}>",
                            lines[last_line-1].strip()
                        ))
                        # Remove from stack to avoid cascading errors
                        stack.pop()

    # Report any remaining unclosed tags
    for tag, line_num, col in stack:
        errors.append((
            "Reptag-balance",
            line_num,
            col,
            f"Unclosed tag <{tag}> at end of document",
            lines[line_num-1].strip()
        ))
    
    return errors

def validate_tags(tree, allowed_tags=None, non_closing_tags=None, line_mapping=None):
    """Validate tags while considering balancing"""
    errors = []
    if tree is None:
        return errors

    root = tree.getroot()
    
    # First get balancing errors from the raw content
    raw_content = etree.tostring(tree, encoding='unicode')
    balance_errors = check_tag_balancing(raw_content)
    errors.extend(balance_errors)
    
    # Then check other tag validation rules
    for elem in root.iter():
        tag = elem.tag
        parent = elem.getparent()
        parent_tag = parent.tag if parent is not None else None

        line = elem.sourceline or 0
        col = getattr(elem, "sourcepos", 0)
        orig_line = line_mapping.get(line, line) if line_mapping else line

        # Skip if this was already reported as a balance error
        if any(e[1] == orig_line and e[2] == col for e in balance_errors):
            continue

        # Other validation checks...
        if allowed_tags and tag not in allowed_tags:
            errors.append((
                "Reptag",
                orig_line,
                col,
                f"Unsupported tag <{tag}> found"
            ))

        # Add other validation rules as needed...
    
    return errors


def check_tag_nesting(file_content):
    errors = []
    stack = []
    lines = file_content.splitlines()
    tag_pattern = re.compile(r'<(/?)([a-zA-Z0-9]+)[^>]*>')

    for line_num, line in enumerate(lines, 1):
        for match in tag_pattern.finditer(line):
            is_closing = match.group(1) == '/'
            tag = match.group(2)
            col = match.start() + 1

            if tag not in BALANCED_TAGS:
                continue

            if not is_closing:
                # Check for invalid parent-child relationship
                if stack:
                    parent_tag = stack[-1][0]
                    if (parent_tag in INVALID_NESTING_RULES and 
                        tag in INVALID_NESTING_RULES[parent_tag]):
                        errors.append((
                            "Reptag", line_num, col,
                            f"Invalid nesting: <{tag}> should not be inside <{parent_tag}>"
                        ))
                        # Don't push invalid nesting to stack
                        continue
                stack.append((tag, line_num, col))
            else:
                if not stack:
                    errors.append(("Reptag", line_num, col, f"Unexpected closing tag </{tag}>"))
                    continue
                
                # Find the most recent matching opening tag in the stack
                found = False
                for i in range(len(stack)-1, -1, -1):
                    if stack[i][0] == tag:
                        # Found matching opening tag
                        found = True
                        # Remove this item and any unclosed tags after it
                        stack = stack[:i]
                        break
                
                if not found:
                    errors.append((
                        "Reptag", line_num, col,
                        f"Mismatched nesting: found </{tag}> but no matching opening tag"
                    ))

    for unclosed_tag, line_num, col in stack:
        errors.append(("Reptag", line_num, col, f"Unclosed tag <{unclosed_tag}>"))

    return errors

def check_cross_page_tags(file_content):
    """
    Ensures that tags opened in one <Page> block are closed within the same page.
    """
    errors = []
    lines = file_content.splitlines()

    tag_stack = []  # Stack of (tag, page_num, line_num, col)
    page_line_map = {}  # line_num → page_num

    current_page = "1"
    for line_num, line in enumerate(lines, 1):
        page_match = re.search(r'<Page\s+(\d+)\s*>', line, re.IGNORECASE)
        if page_match:
            current_page = page_match.group(1)
        page_line_map[line_num] = current_page

    tag_pattern = re.compile(r'<(/?)([A-Za-z][A-Za-z0-9]*)(?:\s[^>]*?)?>')

    for line_num, line in enumerate(lines, 1):
        for match in tag_pattern.finditer(line):
            is_closing = match.group(1) == '/'
            tag_name = match.group(2)
            col = match.start() + 1
            page_num = page_line_map.get(line_num, "1")

            if is_closing:
                # Try to match with top of stack
                for i in range(len(tag_stack) - 1, -1, -1):
                    t, pg, ln, cl = tag_stack[i]
                    if t == tag_name:
                        if pg != page_num:
                            errors.append((
                                "Reptag",
                                ln,
                                cl,
                                f"Tag <{tag_name}> opened in Page {pg} but closed in Page {page_num} — must close in same page"
                            ))
                        tag_stack.pop(i)
                        break
            else:
                # Opening tag
                tag_stack.append((tag_name, page_num, line_num, col))

    return errors
