import sys

def unquoted(line, string): 
    # return True if string in line unquoted,
    # False if string not in line or string in quotes
    
    inside = False
    quote_char = ''
    buffer = ''

    for c in line:
        if c in ['"', "'"]:
            if not inside:
                inside = True
                quote_char = c
                buffer = ''
            elif c == quote_char:
                inside = False
                buffer = ''
        else : 
            buffer+=c

        if string in buffer and not inside:
            return True

    return False

def remove_when_in_quotes(line, char):
    
    result = ''
    inside = False
    quote_char = ''

    for c in line:
        if c in ['"', "'"]:
            if not inside:
                inside = True
                quote_char = c
            elif c == quote_char:
                inside = False

        if c!=char or not inside:
            result+=c

    return result

def make_dense(str): return str.replace(' ', '').lower()

filename, clean_dir = sys.argv[1:]
basename = filename.split('/')[-1]

start_keywords = ["module", "endmodule", "program", "endprogram", "contains", "implicitnone", "use", "external"]
in_keywords = ["intent(in", "intent(out)", "subroutine", "function", "public", "private"]
lines_to_keep = []
multiple_line = False
keep_all_lines = True

with open(filename) as f:
    while line:=f.readline():
        keep = False


        if line.lstrip().startswith("#"): 

            keep = True
            lines_to_keep.append([line, keep])

        else:

            line = remove_when_in_quotes(line, '!') # avoid deletion if character "!" in a string

            if "!" in line : 
                line = line.split('!')[0] + "\n" # delete comment from line

            if line.isspace() : # if line is empty, remove it
                continue 
                
            line_dense = make_dense(line) # to simplify search of keywords

            for keyword in start_keywords : 

                if line_dense.startswith(keyword) :
                    keep = True

                    if keyword == 'contains': 

                        keep_all_lines = False

                        for i in range(len(lines_to_keep)):
                            lines_to_keep[i][1] = 'True'

                    break

            for keyword in in_keywords :

                if unquoted(line_dense, keyword) :
                    keep = True

                    if keyword in ['function', 'subroutine']:
                        keep_all_lines = False

                    # keep lines initializing 'target'
                    # where 'target' is function result variable if result(...) exists 
                    # or function name otherwise

                    if unquoted(line_dense, "endfunction") :

                        start = line_dense.find("endfunction") + 11
                        function_name = line_dense[start:].rstrip()
                        prev_line, keep_prev_line = lines_to_keep[-1]
                        i  = -2

                        while not unquoted(make_dense(prev_line), f"function{function_name}"): # move backward to start of function 
                            prev_line, keep_prev_line = lines_to_keep[i]
                            i-=1

                        prev_line_dense = make_dense(prev_line)
        
                        if unquoted(prev_line_dense, "result(") : 
                            start = prev_line_dense.find("result(") + 7
                            end = start + prev_line_dense[start:].find(")") 
                            target = prev_line_dense[start:end]
                        else : 
                            target = function_name

                        for j in range(i+1, -1):
                            func_line_dense = make_dense(lines_to_keep[j][0])
                            if unquoted(func_line_dense,("::")) and unquoted(func_line_dense,(target)):
                                lines_to_keep[j][1] = True

                    # set default values 

                    if unquoted(line_dense, "_alloc") and unquoted(line_dense, "endfunction") :
                        start = line_dense.find("endfunction") + 11
                        end = line_dense.find("_alloc")
                        function_name = line_dense[start:end]
                        lines_to_keep.append([f"{function_name}_alloc=0\n", True])

                    if unquoted(line_dense, "logical,public::ln_"):
                        prefix, vars_part = line.split("::", 1)
                        vars_list = [v.strip() for v in vars_part.split(",")]

                        for i, v in enumerate(vars_list):
                            if v.startswith("ln_") and '=' not in v:
                                vars_list[i] = f"{v} = .FALSE."
                        
                        line = f"{prefix}:: " + ", ".join(vars_list)+"\n"

                    break

            # combining continuation lines in one 

            # !!! potential issue if continuation line interrupted by "#"
            # or by end of file
            # to fix 
            
            if line_dense.rstrip().endswith("&"):
                if not multiple_line: # start multi-line
                    combined_line = line[:line.rfind("&")]
                    combined_keep = keep
                    multiple_line = True
                else: # continue multi-line
                    if line_dense.lstrip().startswith("&"):
                        combined_line += line[line.find("&")+1:line.rfind("&")]
                    else :
                        combined_line += " "+line[:line.rfind("&")]
                    combined_keep  = combined_keep or keep

            elif multiple_line : # end multi-line
                combined_line += line[line.find("&")+1:]
                combined_keep = combined_keep or keep
                multiple_line = False
                lines_to_keep.append([combined_line, combined_keep])

            else: 
                lines_to_keep.append([line, keep])

# special cases

if basename.lower() == 'sbc_oce.f90':
    for i in range(len(lines_to_keep)) : 
        line_dense  = make_dense(lines_to_keep[i][0])
        if line_dense.startswith("allocate") or line_dense.startswith("integer::ierr"):
            lines_to_keep[i][1]  = True
        lines_to_keep[i][0] = lines_to_keep[i][0].replace("nn_ice", "nn_ice = 0")

elif basename.lower() == 'sbcmod.f90' :
    for i in range(len(lines_to_keep)) : 
        line_dense  = make_dense(lines_to_keep[i][0])
        if line_dense.startswith("utauu(ji,jj)"):
            for j in range(i-1, i+3): lines_to_keep[j][1]  = True
        elif line_dense.startswith("integer::j") or unquoted(line_dense, "sbc_oce_alloc()"):
            lines_to_keep[i][1]  = True
        elif unquoted(line_dense, "callusrdef_sbc_oce"):
            line = lines_to_keep[i][0]
            start = line.find("usrdef_sbc_oce")
            lines_to_keep[i] = ["CALL "+line[start:], True]

clean_file = ''
for line, keep in lines_to_keep : 
    # if no contains, subroutine or function
    # keep everything
    if keep or keep_all_lines : clean_file += line 

with open(f"{clean_dir}/{basename}", "w") as f:
    f.write(clean_file)
