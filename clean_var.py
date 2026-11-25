import sys
import re 

filename, clean_dir, *vars = sys.argv[1:]
basename = filename.split('/')[-1]

with open(filename) as f:
    lines = f.readlines()

for i in range(len(lines)):
    vars_to_remove = []
    for var in vars:

        line = lines[i]
        nb_brackets = 0
        pattern = re.compile(f"\\b{var}\\b") # avoid matching if another variable contains variable name 
        match = pattern.search(line)

        if match : 

            start, stop = match.span()

            for j in range(stop,len(line)) :
                if line[j] == ',' and nb_brackets == 0:
                    lines[i] = line[:start]+line[j+1:] 
                    break
                if line[j] == '(': nb_brackets += 1
                if line[j] == ')': nb_brackets -= 1
                
            if j == len(line)-1:
                new_line = line[:start].rstrip()
                if new_line.endswith(','): # avoid trailing commas
                    new_line = new_line[:-1]
                lines[i] = new_line+'\n'
            
            vars_to_remove.append(var)

    vars = [v for v in vars if v not in vars_to_remove]

    if len(vars) == 0:
        break # stop search when all variables are found once
        

with open(f"{clean_dir}/{basename}", "w") as f:
    f.writelines(lines)
