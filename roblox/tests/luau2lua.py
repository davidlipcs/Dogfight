"""A small Luau -> Lua 5.4 translator for the tests (the Roblox-side code is run under lupa with a mock of the Roblox API, see mockrbx.lua).
Handles what the project's code uses: compound assignment, type annotations on parameters / returns / locals, `export type`, the generic for over
a table, `continue` is not used.  Strings and comments are left alone."""
import re
import sys


def protect(src):
    """replace string literals and comments by placeholders; returns (code, table)"""
    out, table, i, n = [], [], 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith('--[[', i) or src.startswith('--[=[', i):
            m = re.match(r'--\[(=*)\[', src[i:])
            end = src.index(']' + m.group(1) + ']', i) + len(m.group(1)) + 2
            out.append('\n' * src[i:end].count('\n'))
            i = end
        elif src.startswith('--', i):
            j = src.find('\n', i)
            j = n if j < 0 else j
            i = j
        elif c in '"\'':
            j = i + 1
            while src[j] != c:
                j += 2 if src[j] == '\\' else 1
            table.append(src[i:j + 1])
            out.append('\x01%d\x02' % (len(table) - 1))
            i = j + 1
        elif src.startswith('[[', i) or re.match(r'\[=+\[', src[i:i + 4] or ''):
            m = re.match(r'\[(=*)\[', src[i:])
            end = src.index(']' + m.group(1) + ']', i) + len(m.group(1)) + 2
            table.append(src[i:end])
            out.append('\x01%d\x02' % (len(table) - 1))
            i = end
        else:
            out.append(c)
            i += 1
    return ''.join(out), table


def strip_types_in_params(params):
    parts, depth, cur = [], 0, ''
    for ch in params:
        if ch in '({<':
            depth += 1
        elif ch in ')}>':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(cur)
            cur = ''
        else:
            cur += ch
    parts.append(cur)
    out = []
    for p in parts:
        name = p.split(':')[0].strip()
        out.append(name)
    return ', '.join(out)


def fix_functions(code):
    res, i = [], 0
    for m in re.finditer(r'\bfunction\b\s*([\w\.:]*)\s*\(', code):
        pass
    pos = 0
    out = []
    pat = re.compile(r'\bfunction\b\s*([\w\.:]*)\s*\(')
    while True:
        m = pat.search(code, pos)
        if not m:
            out.append(code[pos:])
            break
        out.append(code[pos:m.end()])
        # matching paren
        j, depth = m.end(), 1
        while depth:
            if code[j] == '(':
                depth += 1
            elif code[j] == ')':
                depth -= 1
            j += 1
        params = code[m.end():j - 1]
        out.append(strip_types_in_params(params) + ')')
        # return type: ": T" up to the end of the line (functions with a return type have their body on the following lines)
        k = j
        mm = re.match(r'[ \t]*:[ \t]*([^\n]*?)[ \t]*(?=\n)', code[k:])
        if mm:
            k += mm.end()
        pos = k
    return ''.join(out)


def translate(src):
    code, table = protect(src)
    code = re.sub(r'^\s*export type [^\n]*\n', '\n', code, flags=re.M)
    code = fix_functions(code)
    # local x: T = ...   /   local x: T
    code = re.sub(r'(\blocal\s+[\w, ]+?)\s*:\s*[^=\n]+?(\s*=)', r'\1\2', code)
    code = re.sub(r'(\blocal\s+\w+)\s*:\s*[^\n=]+$', r'\1', code, flags=re.M)
    # casts
    code = re.sub(r'\s::\s*[\w\.\?\{\}<> ]+', '', code)
    # compound assignment (single statements)
    def comp(m):
        lhs, op, rhs = m.group(2), m.group(3), m.group(4)
        return '%s%s = %s %s (%s)' % (m.group(1), lhs, lhs, op, rhs)
    code = re.sub(r'^([ \t]*)([\w\.\[\]"\x01\x02]+)[ \t]*(\+|-|\*|/|//|%|\^)=[ \t]*(.+)$', comp, code, flags=re.M)
    code = re.sub(r'([A-Za-z_][\w\.]*)[ \t]*(\+|-|\*|/)=[ \t]*([^\s]+)', r'\1 = \1 \2 \3', code)
    # generic for over a value
    def gfor(m):
        names, rhs = m.group(1), m.group(2).strip()
        if re.match(r'(ipairs|pairs|next|string\.gmatch|__it)\b', rhs) or rhs.endswith('gmatch'):
            return m.group(0)
        return 'for %s in __it(%s) do' % (names, rhs)
    code = re.sub(r'for ([\w, ]+) in ([^\n]+?) do\b', gfor, code)
    # restore strings
    code = re.sub(r'\x01(\d+)\x02', lambda m: table[int(m.group(1))], code)
    return code


if __name__ == '__main__':
    sys.stdout.write(translate(open(sys.argv[1], encoding='utf-8').read()))
