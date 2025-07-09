import re
from config import CUSTOM_ENTITIES, SUPPORTED_TAGS

DEFAULT_ENTITIES = {
    'amp', 'lt', 'gt', 'quot', 'apos',
    'mdash', 'sect', 'nbsp', 'copy'  # Add more as needed
}

def check_entities(file_content, custom_entities=None):
    """
    Entity checker that focuses ONLY on invalid entities (ignores unescaped chars)
    Checks for:
    - Invalid named entities
    - Does NOT check for unescaped <, >, or & characters
    """
    errors = []
    lines = file_content.splitlines()
    allowed_entities = DEFAULT_ENTITIES.union(custom_entities or set())
    
    # Pattern to match XML/SGML tags
    tag_pattern = re.compile(r'<\/?[a-zA-Z][a-zA-Z0-9]*(\s+[^>]*)?>')
    # Pattern to match both named and numeric entities
    entity_pattern = re.compile(r'&(#[0-9]+|#x[0-9a-fA-F]+|[a-zA-Z0-9]+);')

    for line_num, line in enumerate(lines, 1):
        # First find all valid tags in the line
        tag_positions = []
        for match in tag_pattern.finditer(line):
            tag_positions.append((match.start(), match.end()))
        
        # Check for invalid named entities only
        for match in entity_pattern.finditer(line):
            entity = match.group(1)
            # Only validate named entities (ignore numeric entities)
            if not entity.startswith('#') and entity not in allowed_entities:
                # Check if this is inside a tag (like an attribute)
                inside_tag = any(start <= match.start() <= end for start, end in tag_positions)
                if not inside_tag:
                    col = match.start() + 1
                    errors.append(("Repent", line_num, col, 
                                 f"Invalid entity '&{entity};'"))
    errors.extend(check_table_spacing(file_content))   
    
    return errors         
def check_table_spacing(file_content):
    """
    Flags 2+ continuous spaces inside <EMB>...</EMB> tags within <T> or <A> table blocks.
    Groups all excessive spacing per line per tag to reduce clutter.
    """
    errors = []
    lines = file_content.splitlines()
    in_table = False
    processed_lines = set()

    # ✅ Fix here: match both <T> and <A> tags
    table_tag_pattern = re.compile(r'<\s*/?(T|A)\s*>', re.IGNORECASE)
    emb_tag_pattern = re.compile(r'<(EMB[^>]*)>(.*?)<\/\1>', re.IGNORECASE | re.DOTALL)
    space_pattern = re.compile(r'\s{2,}')

    current_table_lines = []
    current_line_num = 0

    for line_num, line in enumerate(lines, 1):
        if table_tag_pattern.search(line):
            if re.search(r'</\s*(T|A)\s*>', line, re.IGNORECASE):
                # We reached end of a table
                table_content = '\n'.join(current_table_lines)
                for tag_match in emb_tag_pattern.finditer(table_content):
                    tag_content = tag_match.group(2)
                    if space_pattern.search(tag_content):
                        abs_pos = tag_match.start(2)
                        pos_counter = 0
                        line_offset = 0
                        for i, table_line in enumerate(current_table_lines):
                            if pos_counter + len(table_line) >= abs_pos:
                                line_offset = i
                                break
                            pos_counter += len(table_line) + 1  # newline

                        error_line_num = current_line_num + line_offset
                        if error_line_num not in processed_lines:
                            processed_lines.add(error_line_num)
                            errors.append((
                                "Reptab",
                                error_line_num,
                                1,
                                f"Excessive spacing inside <{tag_match.group(1)}> tag"
                            ))

                in_table = False
                current_table_lines = []
            elif re.search(r'<\s*(T|A)\s*>', line, re.IGNORECASE):
                in_table = True
                current_line_num = line_num
                current_table_lines = [line]
            continue

        if in_table:
            current_table_lines.append(line)

    return errors

