from lxml import etree
from entity_checker import check_entities
from config import SUPPORTED_TAGS, NON_CLOSING_TAGS, TAG_RELATIONSHIPS, BALANCED_TAGS
from lxml.etree import _Element
import logging
import re

logger = logging.getLogger(__name__)


def validate_tags(tree, allowed_tags=None, non_closing_tags=None, line_mapping=None):
    errors = []
    if tree is None:
        return errors

    root = tree.getroot()

    def is_fnt_variant(tag):
        """Returns True if tag is any fnt variant (fnt, fnt*, fnt1, fnt2, etc.)"""
        tag_lower = tag.lower()
        return (tag_lower.startswith('fnt') and 
                (tag_lower in {'fnt', 'fnt*'} or 
                 tag_lower[3:].isdigit()))

    def is_non_closing(tag):
        """Returns True if tag is a non-closing tag (fnt*, fnr*, etc.)"""
        tag_lower = tag.lower()
        non_closing_tags_lower = {t.lower() for t in (non_closing_tags or NON_CLOSING_TAGS)}
        return any(
            tag_lower == base_tag.lower() or
            (base_tag.endswith('*') and tag_lower.startswith(base_tag.rstrip('*').lower())) or
            (base_tag[:-1].isdigit() and tag_lower == base_tag.lower()[:-1])
            for base_tag in non_closing_tags_lower
        )

    # First pass: Validate all elements
    for elem in root.iter():
        tag = elem.tag
        parent = elem.getparent()
        parent_tag = parent.tag if parent is not None else None

        line = elem.sourceline or 0
        col = getattr(elem, "sourcepos", 0)
        orig_line = line_mapping.get(line, line) if line_mapping else line

        # ✅ Rule 0: Disallow unknown tags
        if allowed_tags and tag not in allowed_tags:
            errors.append((
                "Reptag",
                orig_line,
                col,
                f"Unsupported tag <{tag}> found"
            ))

        # Rule 1: Any fnt variant must be inside FN
        if is_fnt_variant(tag) and parent_tag != 'FN':
            errors.append((
                "Reptag",
                orig_line,
                col,
                f"<{tag}> must be inside <FN> tags (found outside)"
            ))

        # Rule 2: fnt variants cannot have closing tags (even inside FN)
        if is_fnt_variant(tag) and elem.tail and '</' + tag.lower() + '>' in elem.tail.lower():
            errors.append((
                "Reptag",
                orig_line,
                col,
                f"<{tag}> is a non-closing tag (do not use </{tag}>)"
            ))

        # Rule 3: Only fnt variants allowed inside FN
        if parent_tag == 'FN' and not is_fnt_variant(tag) and tag.lower() != 'fn':
            errors.append((
                "Reptag",
                orig_line,
                col,
                f"Only <fnt*> tags allowed inside <FN>, found <{tag}>"
            ))

    # Second pass: Validate FN nesting structure
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
    Checks if all BALANCED_TAGS are properly opened and closed using a stack-based approach.
    """
    stack = []
    errors = []
    lines = file_content.splitlines()

    tag_pattern = re.compile(r'<(/?)([a-zA-Z0-9]+)[^>]*>')

    for line_num, line in enumerate(lines, 1):
        for match in tag_pattern.finditer(line):
            is_closing = match.group(1) == "/"
            tag_name = match.group(2)

            if tag_name in BALANCED_TAGS:
                if not is_closing:
                    stack.append((tag_name, line_num))
                else:
                    if not stack:
                        errors.append((
                            "Reptag", line_num, match.start() + 1,
                            f"Unexpected closing tag </{tag_name}>"
                        ))
                    else:
                        last_tag, last_line = stack.pop()
                        if last_tag != tag_name:
                            errors.append((
                                "Reptag", line_num, match.start() + 1,
                                f"Tag mismatch: expected </{last_tag}> but found </{tag_name}>"
                            ))

    for tag, line_num in stack:
        errors.append((
            "Reptag", line_num, 1, f"Unclosed tag <{tag}>"
        ))

    return errors


def check_tag_nesting(file_content):
    """
    Checks for proper nesting of BALANCED_TAGS using a stack.
    Flags unclosed, mismatched, or improperly nested tags.
    """
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
                stack.append((tag, line_num, col))
            else:
                if not stack:
                    errors.append(("Reptag", line_num, col, f"Unexpected closing tag </{tag}>"))
                    continue
                last_tag, last_line, last_col = stack[-1]
                if last_tag == tag:
                    stack.pop()
                else:
                    errors.append(("Reptag", line_num, col,
                                   f"Mismatched nesting: found </{tag}> but expected </{last_tag}> to close <{last_tag}> opened at line {last_line}"))
                    stack.pop()

    for unclosed_tag, line_num, col in stack:
        errors.append(("Reptag", line_num, col, f"Unclosed tag <{unclosed_tag}>"))

    return errors
