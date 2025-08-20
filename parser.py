from lxml import etree
import re

# ========== CLEANER ==========
def preprocess_file_content(raw_content):
    """Fix layout markers and dynamic non-closing tags for XML compatibility."""
    page_tag_pattern = re.compile(r"<\s*Page\s+\d+\s*>", re.IGNORECASE)
    non_closing_tag_pattern = {"fnt","fnr"}

    head_foot = {"\*\*\*\*HEADNOTE\*\*\*\*","\*\*\*\*FOOTNOTE\*\*\*\*"}

    layout_tags = {"P20", "CN", "HN02", "HN24", "P00","B22", "HN68","P02", "B24", "HN46",
                  "B42", "P24", "P42", "B44", "B", "C5", "HN00", "HN20"}

    cleaned_lines = []
    for line in raw_content.splitlines():
        line = page_tag_pattern.sub("<Page/>", line)

    #  Remove all <SPage ...> tags
        line = re.sub(r"<\s*SPage\b[^>]*>", "", line, flags=re.IGNORECASE)

    # Fix layout tags
        for tag in layout_tags:
            line = re.sub(rf"<\s*{tag}(\s[^>]*)?>", rf"<{tag}\1/>", line)

        for tag in non_closing_tag_pattern:
            line = re.sub(rf"<\s*{tag}[^/>]*(\s[^>]*)?>", rf"<{tag}\1/>", line)

        for tag in head_foot:
            line = re.sub(rf"<\s*{tag}(\s[^>]*)?>", rf"", line)

        line = re.sub("\r\n\r\n", "", line)

        cleaned_lines.append(line)



    return "\n".join(cleaned_lines)

# ========== ENTITY CONVERTER ==========
ENTITY_TO_NUMERIC = {
    # Special characters
    "cacute": "&#263;", "itilde": "&#297;", "Lstrok": "&#321;", "nacute": "&#324;",
    "Sacute": "&#346;", "sacute": "&#347;", "Agrave": "&#192;", "Aacute": "&#193;",
    "Acirc": "&#194;", "Atilde": "&#195;", "Auml": "&#196;", "Aring": "&#197;",
    "AElig": "&#198;", "Ccedil": "&#199;", "Egrave": "&#200;", "Eacute": "&#201;",
    "Ecirc": "&#202;", "Euml": "&#203;", "Igrave": "&#204;", "Iacute": "&#205;",
    "Icirc": "&#206;", "Iuml": "&#207;", "ETH": "&#208;", "Ntilde": "&#209;",
    "Ograve": "&#210;", "Oacute": "&#211;", "Ocirc": "&#212;", "Otilde": "&#213;",
    "Ouml": "&#214;", "Oslash": "&#216;", "Ugrave": "&#217;", "Uacute": "&#218;",
    "Ucirc": "&#219;", "Uuml": "&#220;", "Yacute": "&#221;", "THORN": "&#222;",
    "szlig": "&#223;", "agrave": "&#224;", "aacute": "&#225;", "acirc": "&#226;",
    "atilde": "&#227;", "auml": "&#228;", "aring": "&#229;", "aelig": "&#230;",
    "ccedil": "&#231;", "egrave": "&#232;", "eacute": "&#233;", "ecirc": "&#234;",
    "euml": "&#235;", "igrave": "&#236;", "iacute": "&#237;", "icirc": "&#238;",
    "iuml": "&#239;", "eth": "&#240;", "ntilde": "&#241;", "ograve": "&#242;",
    "oacute": "&#243;", "ocirc": "&#244;", "otilde": "&#245;", "ouml": "&#246;",
    "oslash": "&#248;", "ugrave": "&#249;", "uacute": "&#250;", "ucirc": "&#251;",
    "uuml": "&#252;", "yacute": "&#253;", "thorn": "&#254;", "yuml": "&#255;",
    
    # Extended Latin
    "abreve": "&#259;", "Abreve": "&#258;", "amacr": "&#257;", "Amacr": "&#256;",
    "aogon": "&#261;", "Aogon": "&#260;", "Cacute": "&#262;", "ccaron": "&#269;",
    "Ccaron": "&#268;", "ccirc": "&#265;", "Ccirc": "&#264;", "cdot": "&#267;",
    "Cdot": "&#266;", "dcaron": "&#271;", "Dcaron": "&#270;", "dstrok": "&#273;",
    "Dstrok": "&#272;", "ecaron": "&#283;", "Ecaron": "&#282;", "edot": "&#279;",
    "Edot": "&#278;", "emacr": "&#275;", "Emacr": "&#274;", "eogon": "&#281;",
    "Eogon": "&#280;", "gacute": "&#501;", "gbreve": "&#287;", "Gbreve": "&#286;",
    "Gcedil": "&#290;", "gcirc": "&#285;", "Gcirc": "&#284;", "gdot": "&#289;",
    "Gdot": "&#288;", "hcirc": "&#293;", "Hcirc": "&#292;", "hstrok": "&#295;",
    "Hstrok": "&#294;", "Idot": "&#304;", "Imacr": "&#298;", "imacr": "&#299;",
    "ijlig": "&#307;", "IJlig": "&#306;", "inodot": "&#305;", "iogon": "&#303;",
    "Iogon": "&#302;", "Itilde": "&#296;", "jcirc": "&#309;", "Jcirc": "&#308;",
    "kcedil": "&#311;", "Kcedil": "&#310;", "kgreen": "&#312;", "lacute": "&#314;",
    "Lacute": "&#313;", "lcaron": "&#318;", "Lcaron": "&#317;", "lcedil": "&#316;",
    "Lcedil": "&#315;", "lmidot": "&#320;", "Lmidot": "&#319;", "lstrok": "&#322;",
    "Nacute": "&#323;", "eng": "&#331;", "ENG": "&#330;", "napos": "&#329;",
    "ncaron": "&#328;", "Ncaron": "&#327;", "ncedil": "&#326;", "Ncedil": "&#325;",
    "odblac": "&#337;", "Odblac": "&#336;", "Omacr": "&#332;", "omacr": "&#333;",
    "oelig": "&#339;", "OElig": "&#338;", "racute": "&#341;", "Racute": "&#340;",
    "rcaron": "&#345;", "Rcaron": "&#344;", "rcedil": "&#343;", "Rcedil": "&#342;",
    "scaron": "&#353;", "Scaron": "&#352;", "scedil": "&#351;", "Scedil": "&#350;",
    "scirc": "&#349;", "Scirc": "&#348;", "tcaron": "&#357;", "Tcaron": "&#356;",
    "tcedil": "&#355;", "Tcedil": "&#354;", "tstrok": "&#359;", "Tstrok": "&#358;",
    "ubreve": "&#365;", "Ubreve": "&#364;", "udblac": "&#369;", "Udblac": "&#368;",
    "umacr": "&#363;", "Umacr": "&#362;", "uogon": "&#371;", "Uogon": "&#370;",
    "uring": "&#367;", "Uring": "&#366;", "utilde": "&#361;", "Utilde": "&#360;",
    "wcirc": "&#373;", "Wcirc": "&#372;", "ycirc": "&#375;", "Ycirc": "&#374;",
    "Yuml": "&#376;", "zacute": "&#378;", "Zacute": "&#377;", "zcaron": "&#382;",
    "Zcaron": "&#381;", "zdot": "&#380;", "Zdot": "&#379;",
    
    # Spacing
    "emsp": "&#8195;", "ensp": "&#8194;", "emsp13": "&#8196;", "emsp14": "&#8197;",
    "numsp": "&#8199;", "puncsp": "&#8200;", "thinsp": "&#8201;", "hairsp": "&#8202;",
    "mdash": "&#8212;", "ndash": "&#8211;", "dash": "&#8208;", "blank": "&#9251;",
    "hellip": "&#8230;", "nldr": "&#8229;",
    
    # Shapes/blocks
    "block": "&#9608;", "uhblk": "&#9600;", "lhblk": "&#9604;", "blk14": "&#9617;",
    "blk12": "&#9618;", "blk34": "&#9619;", "marker": "&#9642;", "cir": "&#9675;",
    "squ": "&#9632;", "rect": "&#9645;", "utri": "&#9650;", "dtri": "&#9660;",
    "star": "&#9734;", "bull": "&#8226;", "squf": "&#9642;", "utrif": "&#9652;",
    "dtrif": "&#9662;", "ltrif": "&#9666;", "rtrif": "&#9656;",
    
    # Cards/suits
    "clubs": "&#9827;", "diams": "&#9830;", "hearts": "&#9829;", "spades": "&#9824;",
    
    # Symbols
    "malt": "&#10016;", "dagger": "&#8224;", "Dagger": "&#8225;", "check": "&#10003;",
    "cross": "&#10007;", "sharp": "&#9839;", "flat": "&#9837;", "male": "&#9794;",
    "female": "&#9792;", "phone": "&#9742;", "telrec": "&#8981;", "copysr": "&#8471;",
    "caret": "&#8257;", "lsquor": "&#8218;", "ldquor": "&#8222;", "fflig": "&#64256;",
    "filig": "&#64257;", "fjlig": "&#64258;", "ffilig": "&#64259;", "ffllig": "&#64260;",
    "fllig": "&#64260;", "mldr": "&#8230;", "rdquor": "&#8221;", "rsquor": "&#8217;",
    "vellip": "&#8942;", "hybull": "&#8259;", "loz": "&#9674;", "lozf": "&#10023;",
    "ltri": "&#9666;", "rtri": "&#9656;", "starf": "&#9733;", "natur": "&#9838;",
    "rx": "&#8478;", "sext": "&#10038;", "target": "&#9678;", "dlcrop": "&#8973;",
    "drcrop": "&#8972;", "ulcrop": "&#8975;", "urcrop": "&#8974;",
    
    # Math
    "scriptE": "&#8496;", "le": "&#8804;", "leEq": "&#8806;", "ge": "&#8805;",
    "radic": "&#8730;", "half": "&#189;", "frac12": "&#189;", "frac14": "&#188;",
    "frac34": "&#190;", "rlarr2": "&#8644;", "swungdash": "&#732;", "approx": "&#8776;",
    "cuwed": "&#8911;", "sup1": "&#185;", "sup2": "&#178;", "sup3": "&#179;",
    "plus": "&#43;", "plusmn": "&#177;", "equals": "&#61;", "gt": "&#62;",
    "divide": "&#247;", "times": "&#215;", "curren": "&#164;",
    
    # Currency
    "pound": "&#163;", "dollar": "&#36;", "cent": "&#162;", "yen": "&#165;",
    "num": "&#8470;", "percnt": "&#37;", "ast": "&#42;", "commat": "&#64;",
    
    # Brackets
    "lsqb": "&#91;", "bsol": "&#92;", "rsqb": "&#93;", "lcub": "&#123;",
    "horbar": "&#8213;", "verbar": "&#124;", "rcub": "&#125;",
    
    # Units
    "micro": "&#181;", "ohm": "&#937;", "deg": "&#176;", "ordm": "&#186;",
    "ordf": "&#170;", "sect": "&#167;", "para": "&#182;", "middot": "&#183;",
    
    # Arrows
    "larr": "&#8592;", "rarr": "&#8594;", "uarr": "&#8593;", "darr": "&#8595;",
    
    # Legal
    "copy": "&#169;", "reg": "&#174;", "trade": "&#8482;", "brvbar": "&#166;",
    "not": "&#172;", "sung": "&#9834;",
    
    # Punctuation
    "excl": "&#33;", "iexcl": "&#161;", "quot": "&#34;", "apos": "&#39;",
    "lpar": "&#40;", "rpar": "&#41;", "comma": "&#44;", "lowbar": "&#95;",
    "hyphen": "&#45;", "period": "&#46;", "sol": "&#47;", "colon": "&#58;",
    "semi": "&#59;", "quest": "&#63;", "iquest": "&#191;", "lsquo": "&#8216;",
    "rsquo": "&#8217;", "ldquo": "&#8220;", "rdquo": "&#8221;", "nbsp": "&#160;",
    "shy": "&#173;", "schwa": "&#601;",
    
    # Greek
    "alpha": "&#945;", "Alpha": "&#913;", "beta": "&#946;", "Beta": "&#914;",
    "gamma": "&#947;", "Gamma": "&#915;", "delta": "&#948;", "Delta": "&#916;",
    "epsilon": "&#949;", "Epsilon": "&#917;", "zeta": "&#950;", "Zeta": "&#918;",
    "eta": "&#951;", "Eta": "&#919;", "theta": "&#952;", "Theta": "&#920;",
    "iota": "&#953;", "Iota": "&#921;", "kappa": "&#954;", "Kappa": "&#922;",
    "lambda": "&#955;", "Lambda": "&#923;", "mu": "&#956;", "Mu": "&#924;",
    "nu": "&#957;", "Nu": "&#925;", "xi": "&#958;", "Xi": "&#926;",
    "omicron": "&#959;", "Omicron": "&#927;", "pi": "&#960;", "Pi": "&#928;",
    "rho": "&#961;", "Rho": "&#929;", "fsigma": "&#962;", "sigma": "&#963;",
    "Sigma": "&#931;", "tau": "&#964;", "Tau": "&#932;", "upsilon": "&#965;",
    "Upsilon": "&#933;", "phi": "&#966;", "Phi": "&#934;", "chi": "&#967;",
    "Chi": "&#935;", "psi": "&#968;", "Psi": "&#936;", "omega": "&#969;",
    "Omega": "&#937;",
    
    # Diacritics
    "aacgr": "&#940;", "Aacgr": "&#902;", "eacgr": "&#941;", "Eacgr": "&#904;",
    "eeacgr": "&#942;", "EEacgr": "&#905;", "idigr": "&#943;", "Idigr": "&#906;",
    "iacgr": "&#943;", "Iacgr": "&#906;", "idiagr": "&#943;", "oacgr": "&#972;",
    "Oacgr": "&#908;", "udigr": "&#973;", "Udigr": "&#910;", "uacgr": "&#973;",
    "Uacgr": "&#910;", "udiagr": "&#973;", "Udiagr": "&#910;", "ohacgr": "&#974;",
    "OHacgr": "&#911;",
    
    # Math symbols
    "aleph": "&#8501;", "and": "&#8743;", "ang90": "&#8735;", "angsph": "&#8738;",
    "ap": "&#8776;", "becaus": "&#8757;", "bottom": "&#8869;", "cap": "&#8745;",
    "cong": "&#8773;", "conint": "&#8750;", "cup": "&#8746;", "equiv": "&#8801;",
    "exist": "&#8707;", "forall": "&#8704;", "fnof": "&#402;", "iff": "&#8660;",
    "infin": "&#8734;", "int": "&#8747;", "isin": "&#8712;", "lang": "&#10216;",
    "lArr": "&#8656;", "minus": "&#8722;", "mnplus": "&#8723;", "nabla": "&#8711;",
    "ne": "&#8800;", "ni": "&#8715;", "or": "&#8744;", "par": "&#8741;",
    "part": "&#8706;", "permil": "&#8240;", "perp": "&#8869;", "prime": "&#8242;",
    "Prime": "&#8243;", "prop": "&#8733;", "rang": "&#10217;", "rArr": "&#8658;",
    "sim": "&#8764;", "sime": "&#8771;", "square": "&#9633;", "sub": "&#8834;",
    "sube": "&#8838;", "sup": "&#8835;", "supe": "&#8839;", "there4": "&#8756;",
    "Verbar": "&#8214;", "angst": "&#8491;", "bernou": "&#8492;", "compfn": "&#8728;",
    "Dot": "&#168;", "DotDot": "&#8412;", "hamilt": "&#8459;", "lagran": "&#8466;",
    "lowast": "&#8727;", "notin": "&#8713;", "order": "&#8500;", "phmmat": "&#8499;",
    "tdot": "&#8411;", "tprime": "&#8244;", "wedgeq": "&#8793;", "rdArr": "&#8659;",
    
    # Circles
    "Acircle": "&#9398;", "Bcircle": "&#9399;", "Ccircle": "&#9400;",
    "Dcircle": "&#9401;", "Ecircle": "&#9402;", "Fcircle": "&#9403;",
    "Gcircle": "&#9404;", "Hcircle": "&#9405;", "Icircle": "&#9406;",
    "Jcircle": "&#9407;", "Kcircle": "&#9408;", "Lcircle": "&#9409;",
    "Mcircle": "&#9410;", "Ncircle": "&#9411;", "Ocircle": "&#9412;",
    "Pcircle": "&#9413;", "Qcircle": "&#9414;", "Rcircle": "&#9415;",
    "Scircle": "&#9416;", "Tcircle": "&#9417;", "Ucircle": "&#9418;",
    "Vcircle": "&#9419;", "Wcircle": "&#9420;", "Xcircle": "&#9421;",
    "Ycircle": "&#9422;", "Zcircle": "&#9423;", "acircle": "&#9424;",
    "bcircle": "&#9425;", "ccircle": "&#9426;", "dcircle": "&#9427;",
    "ecircle": "&#9428;", "fcircle": "&#9429;", "gcircle": "&#9430;",
    "hcircle": "&#9431;", "icircle": "&#9432;", "jcircle": "&#9433;",
    "kcircle": "&#9434;", "lcircle": "&#9435;", "mcircle": "&#9436;",
    "ncircle": "&#9437;", "ocircle": "&#9438;", "pcircle": "&#9439;",
    "qcircle": "&#9440;", "rcircle": "&#9441;", "scircle": "&#9442;",
    "tcircle": "&#9443;", "ucircle": "&#9444;", "vcircle": "&#9445;",
    "wcircle": "&#9446;", "xcircle": "&#9447;", "ycircle": "&#9448;",
    "zcircle": "&#9449;", "circle0": "&#9450;", "circle1": "&#9451;",
    "circle2": "&#9452;", "circle3": "&#9453;", "circle4": "&#9454;",
    "circle5": "&#9455;", "circle6": "&#9456;", "circle7": "&#9457;",
    "circle8": "&#9458;", "circle9": "&#9459;", "circle10": "&#9460;",
    "circle11": "&#9461;", "circle12": "&#9462;", "circle13": "&#9463;",
    "circle14": "&#9464;", "circle15": "&#9465;", "circle16": "&#9466;",
    "circle17": "&#9467;", "circle18": "&#9468;", "circle19": "&#9469;",
    "circle20": "&#9470;", "euro": "&#8364;", "laquo": "&#171;", "raquo": "&#187;"
}

def replace_entities_with_numeric(xml_str):
    """Replaces named entities with numeric character references."""
    for entity, numeric in ENTITY_TO_NUMERIC.items():
        xml_str = xml_str.replace(f"&{entity};", numeric)
    return xml_str

# ========== AMPERSAND SANITIZER ==========
def sanitize_unescaped_ampersands(xml_str):
    """
    Replaces unsafe & with &amp;, while preserving:
    - Valid entities (&amp;, &lt;, etc.)
    - Legal-style usage (space & space)
    - Numeric entities (&#123;, &#x1F600;)
    """
    def replacer(match):
        full_match = match.group(0)
        # Skip valid entities
        if full_match.startswith('&#'):
            return full_match
        if full_match in {'&amp;', '&lt;', '&gt;', '&quot;', '&apos;'}:
            return full_match
        # Skip legal-style & surrounded by spaces
        if re.match(r'[ ]&[ ]', full_match):
            return full_match
        # Skip & followed by punctuation
        if re.match(r'&[,.;:)]', full_match):
            return full_match
        return '&amp;'

    return re.sub(r'&(?!#|amp;|lt;|gt;|quot;|apos;|[a-zA-Z0-9]+;)', replacer, xml_str)

# ========== PARSER ==========


def parse_xml(raw_content):
    """
    Parses XML/SGML after cleaning.
    Returns: (tree, errors, None)
    Always returns an ElementTree if parsing succeeds.
    """
    try:
        # STEP 1: Pre-cleaning
        cleaned_content = preprocess_file_content(raw_content)

        # STEP 2: Sanitize
        cleaned_content = sanitize_unescaped_ampersands(cleaned_content)

        # STEP 3: Replace known entities
        cleaned_content = replace_entities_with_numeric(cleaned_content)

        parser = etree.XMLParser(
            recover=False,
            huge_tree=True,
            remove_blank_text=True,
            remove_comments=True,
            resolve_entities=False
        )

        try:
            # 🔑 Try parsing directly (works if file already has one root)
            root = etree.fromstring(cleaned_content.encode("utf-8"), parser)
        except etree.XMLSyntaxError:
            # 🔑 If that fails, fallback to wrapping
            wrapped = f"<root>{cleaned_content}</root>"
            root = etree.fromstring(wrapped.encode("utf-8"), parser)

        tree = etree.ElementTree(root)
        return tree, [], None

    except etree.XMLSyntaxError as e:
        categorized_errors = []
        seen_messages = set()
        lines = raw_content.splitlines()

        for entry in e.error_log:
            msg = entry.message.strip()
            line = entry.line
            col = entry.column
            context = lines[line-1].strip() if 0 < line <= len(lines) else "N/A"

            error_key = (line, col, msg)
            if error_key in seen_messages:
                continue
            seen_messages.add(error_key)

            if "Premature end of data in tag" in msg:
                continue

            lower_msg = msg.lower()
            if any(x in lower_msg for x in ["xmlparseentityref", "unescaped", "no name", "amp", "lt", "gt", "semicolon"]):
                category = "Repent"
            elif "tag mismatch" in lower_msg:
                if "root" in lower_msg:
                    continue
                if "not properly nested" in lower_msg or "misnested" in lower_msg:
                    category = "Reptag-nest"
                else:
                    category = "Reptag-mismatch"
            elif "start tag" in lower_msg or "end tag" in lower_msg:
                category = "Reptag-structure"
            else:
                category = "CheckSGM"

            categorized_errors.append((category, line, col, msg, context))

        categorized_errors.sort(key=lambda x: x[1])
        return None, categorized_errors, None

    except Exception as e:
        return None, [("CheckSGM", 0, 0, f"Unexpected error: {str(e)}", "N/A")], None
