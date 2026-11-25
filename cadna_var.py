import sys
import re

filename, clean_dir, wp_st, *namelist_real_vars = sys.argv[1:]
basename, extension = filename.split('/')[-1].split('.')

# options
st_date = False 
st_coord = True # !!! setting to False does not work yet
st_phycst = False
write_nb_significant_numbers = True

# --- Variables initialization ---

dict_vars_namelist = {}
multiple_line = False
var_inits = []

# special cases of variables initialized elsewhere that cause issues
changed_vars = set(['gdept_1d', 'ght_abl', 'ghw_abl', 'zztmp', 'gdepw_1d', 'e3w_1d', 'adatrj', 'rn_Dt','rDt',\
                    'e1e2t', 'e1e2u', 'e1e2v', 'e1e2f'])

fixed_vars = set([])

# prefixes of variables for which the type must not be changed
fixed_type_var_prefixes = set(['psgn', 'nsgn', 'zsgn', 'class_num', 'basicb_num', \
'EOS', 'ALP', 'BET', 'PEN', 'APE', 'BPE', 'aco_bc_', 'bco_bc_', 'za0', 'za1', 'za2', 'za3', 'zepsilon',\
    'zscf', 'rn_tslsal']) #'zgamma'])

if not st_coord:
    fixed_type_var_prefixes.update(['glam', 'gphi', 'plam', 'pphi'])
else :
    changed_vars.update(['glamf','glamu', 'glamv', 'glamt', 'gphif', 'gphit', 'gphiu', 'gphiv'])

if st_phycst :
    changed_vars.update(['rho0', 'r1_rho0', 'rcp', 'rho0_rcp', 'r1_rho0_rcp', \
                         'rday', 'rmmss', 'rhhmm', 'rjjhh', 'raamo'])

if not st_date : 
    fixed_type_var_prefixes.update(['fjul', 'zsec', 'zjul'])
else : 
    changed_vars.update(['fjulstartyear', 'fjulday'])

# quick fixes

fixed_vars.update(namelist_real_vars)
fixed_vars.discard('rn_Dt')
fixed_vars.discard('rn_si0')
fixed_vars.discard('rn_si1')
fixed_vars.discard('rn_abs')
fixed_vars.discard('rn_zu')
fixed_vars.discard('rn_zqt')
fixed_vars.discard('rn_efac')

if basename == 'fldread': 
    fixed_vars.add('freqh')

if (basename == 'iom' or basename == 'domutl'): 
    fixed_type_var_prefixes.update(['plon', 'plat'])

if (basename == 'domutl'):
    fixed_type_var_prefixes.update(['pt'])

if basename == 'iom':
    fixed_type_var_prefixes.update(['paxis', 'lonvalue', 'latvalue', 'bounds', 'ztmp_pmiss_val', 'zlon'])

# special cases of functions/routines that require real values as arguments
real_functions = ['nint',\
                  'ieee_is_nan', 'errval',\
                  'double_st', 'single_st',\
                  'nf90_put_var', 'nf90_put_att',\
                  'xios_set_axis_attr', 'xios_set_axisgroup_attr', 'xios_send_field', 'xios_recv_field',\
                  'iom_set_domain_attr', 'iom_set_axis_attr','dom_ngb', 'set_mooring', \
                  'set_grid', 'set_grid_bounds', 'set_grid_znl',\
                  'histbeg', 'histvert', 'histwrite', 'iom_put',\
                  'ymds2ju', 'ju2ymds', 'lbnd_ij', 'nf90_get_var', 'nf90_get_att', 'count']

if st_date : real_functions.append('histdef')

# special cases of stochastic functions/routines that are called with real values as arguments
st_functions = ['trc_oce_ext_lev', 'timer_write', 'iom_get', 'tide', 'bdy_dta_tides', 'tsl_tde_pot_upd',\
                'dia_hth_dep', 'dia_hth_htc', 'sign', 'iom_rstput',\
                'fintegral', 'adv_x', 'adv_y', 'adv_z', 'nonosc_ice', 'all_skr_sks',\
                'turb_cd_2z', 'set_hglo_ana']

if basename == 'sbcclo': st_functions.append('merge')

# --- Regex patterns ---

namelist_pattern = re.compile("NAMELIST/([^/]+)/")

# variable types patterns
sp_pattern = re.compile("real *\\( *sp *\\)", re.I)
dp_pattern = re.compile("real *\\( *dp *\\)", re.I)
wp_pattern = re.compile("real *\\( *wp *\\)", re.I)
wph_pattern = re.compile("real *\\((kind *=)? *precision *\\)", re.I)
csp_pattern = re.compile("complex *\\( *sp *\\)", re.I)
cdp_pattern = re.compile("complex *\\( *dp *\\)", re.I)
cwp_pattern = re.compile("complex *\\( *wp *\\)", re.I)

# write command patterns
write_format = "write *\\([^,]+, *(\\w+|\"[^\"]*\"|'[^']*') *\\) *\\(*" # write commands with specific format
write_default_pattern = re.compile("write *\\([^,]+, *\\* *\\) *\\(*", re.I) # write commands with default format

# misc patterns
real_fcn_pattern = re.compile(f"(\\b({'|'.join(real_functions)}) *\\(|{write_format}) *", re.I)
cmplx_pattern = re.compile("\\b(cmplx|real)\\b *\\( *", re.I)
precision_pattern = re.compile("((kind *=)? *\\b[swd]p\\b *| *KIND *| *PREC *| *[48] *)", re.I)
st_fcn_pattern = re.compile(f"\\b({'|'.join(st_functions)}) *\\( *", re.I)
real_nb_pattern = re.compile("^(.*=)? *-?([\\d\\.]+_[wds]p|\\d+\\.\\d*|\\d*\\.\\d+)")

# --- Helper functions ---

def get_type(val):
    val = val.strip()
    if val.endswith("sp"): st_type = "single_st"
    elif val.endswith("dp"): st_type = "double_st"
    else : st_type = wp_st
    return st_type

def split_args(line,start=0,stop=None,replace_blanks=False):
    """
    Split variables separated by commas in a substring of line.

    Args:
        line (str): The full input string.
        start (int): Starting index for parsing.
        stop (int, optional): Ending index (default: end of line).
        replace_blanks (bool, optional): Whether to remove spaces from variables.

    Returns:
        list_vars (list): (list of parsed variables, stopping index)
    """
    if stop is None: stop = len(line)-1

    list_vars = []
    if stop>start :

        nb_brackets = 0
        inside_quotes = False
        quote_char = ''
        j = start 

        while j < stop:

            char = line[j]

            if char == ',' and nb_brackets == 0 and not inside_quotes:
                token = line[start:j]
                list_vars.append(token.replace(' ','') if replace_blanks else token)
                start = j+1

            elif char == '(': 
                nb_brackets += 1

            elif char == ')': 
                nb_brackets -= 1

            elif char in ["'", '"']:
                if not inside_quotes: 
                    inside_quotes = True
                    quote_char = char
                elif char == quote_char:
                    inside_quotes = False
            
            if nb_brackets<0 or char=='!': 
                stop = j
                break

            j+=1
    
    token = line[start:stop]
    list_vars.append(token.replace(' ','') if replace_blanks else token)

    return list_vars, stop

# --- File modification ---

with open(filename) as f:
    lines = [line for line in f.readlines() if (line.strip() and not line.strip().startswith('!'))]

for i, line in enumerate(lines):

    if not st_phycst and basename=="phycst":
        break

    # combine multi-lines in one

    line_no_comment = line.split('!')[0]
    if line_no_comment.rstrip().endswith("&") and i<(len(lines)-1) \
        and lines[i+1].lstrip()[0] not in "!#":
        if not multiple_line: # start multi-line
            combined_line = line[:line_no_comment.rfind("&")]
            multiple_line = True
            lines[i] = ''
            continue

        else: # continue multi-line    
            if line.lstrip().startswith("&"):
                combined_line += line[line.find("&")+1:line_no_comment.rfind("&")].lstrip()
            else :
                combined_line += " "+line[:line_no_comment.rfind("&")].lstrip()
            lines[i] = ''
            continue

    elif multiple_line : # end multi-line
        line = combined_line + line[line.find("&")+1:].lstrip()
        multiple_line = False

    # modify type of real arguments in their initialization

    type_patterns =  [sp_pattern, wp_pattern, dp_pattern, wph_pattern, csp_pattern, cwp_pattern, cdp_pattern]

    for p in type_patterns :
        match = p.search(line)
        if match:

            start = line.find('::')+2
            list_vars, stop = split_args(line, start, replace_blanks=True)

            if not any(v.lstrip().startswith(prefix) for v in list_vars for prefix in fixed_type_var_prefixes) and all('=' not in v for v in list_vars) \
            and not any(v.lstrip() in fixed_vars for v in list_vars) and not (not st_phycst and 'REAL(wp), PARAMETER' in line):

                line = sp_pattern.sub("type(single_st)", line)
                line = dp_pattern.sub("type(double_st)", line)
                line = wp_pattern.sub(f"type({wp_st})", line)

                line = csp_pattern.sub("type(complex_single_st)", line)
                line = cdp_pattern.sub("type(complex_double_st)", line)
                line = cwp_pattern.sub(f"type(complex_{wp_st})", line)

                line = wph_pattern.sub(f"type(REAL_PRECISION)", line)

                st_type = "double_st" if "double_st" in line else "single_st" if "single_st" in line else wp_st
            
                for j, var in enumerate(list_vars):
                    changed_vars.add(var)
                
            else:
                fixed_vars.update([l.split("=")[0] for l in list_vars])

            break
    
    # print stochastic variables in CADNA format

    match = write_default_pattern.search(line)
    if match :

        _, start = match.span()
        list_vars, stop = split_args(line, start)
        for j, var in enumerate(list_vars):
            if var and var.lstrip()[0] not in ["'", '"'] and \
                not any(fn in var.lower() for fn in real_functions):
                for v in changed_vars:
                    v = re.escape(v)
                    v_pattern = re.compile(f"\b{v}\b")
                    if v_pattern.search(var): 
                        list_vars[j] = f"str({list_vars[j]})"
                        break

        line = line[:start]+','.join(list_vars)+line[stop:]

    # modify real arguments of stochastic functions

    match = st_fcn_pattern.search(line)
    new_start = 0
    while match :
        _, start = match.span()
        start += new_start
        list_vars, stop = split_args(line, start)

        for j, var in enumerate(list_vars):
            if (real_nb_pattern.search(var) or var.lstrip() in fixed_vars or \
            (any(var.lstrip().startswith(prefix) for prefix in fixed_type_var_prefixes))) and 'sgn' not in var : 
                if var.count('=') == 1 and not any(op in var for op in ['<=', '>=', '/=']) : # case "fcn(param=0._wp)"
                    name, val = [v.strip() for v in var.split('=')]
                    if name not in fixed_vars and not any(name.lstrip().startswith(prefix) for prefix in fixed_type_var_prefixes):
                        var = f" {name} = {get_type(val)}({val}, {val}, {val})"
                else:  # case "fcn(0._wp)"
                    var = f" {get_type(var)}({var}, {var}, {var})"

            if var.lstrip().lower().startswith('real(') and var.rstrip().endswith(')'):
                var = f" {get_type(var)}({var}, {var}, {var})"

            list_vars[j] = var

        l = line[:start]+','.join(list_vars)
        line, new_start = l+line[stop:], len(l)

        match = st_fcn_pattern.search(line[new_start:])

        
    # modify stochastic arguments of real functions

    match = real_fcn_pattern.search(line)
    new_start = 0
    vars_to_broadcast = []
    
    while match :
        _, start = match.span()
        start += new_start
        list_vars, stop = split_args(line, start)

        if 'histwrite' in match.group(1): #special case for histwrite 
            var = list_vars[3].replace(' ','')
            name_var = list_vars[1].replace(' ','')[1:-1]
            list_vars[3] = f"({var}%x+{var}%y+{var}%z)/3."
            line = line[:start]+','.join(list_vars)+line[stop:]

            if write_nb_significant_numbers:
                indent = line[:line.find('CALL histwrite')]
                if name_var.startswith("vo"):
                    if ":,:,:" in var: arg = var.replace(':,:,:','ji,jj,jk')
                    else: arg  = f"{var}(ji,jj,jk)"
                    line+=f"{indent}DO_3D( 0, 0, 0, 0, 1, jpk ); nbdig3d(ji,jj,jk) = real(nb_significant_digit({arg}), wp); END_3D\n"
                    line+= f'{indent}CALL histwrite( {list_vars[0]}, {list_vars[1].strip()[:-1]}_dig{list_vars[1].strip()[-1]}, kt, nbdig3d, 1, (/-1/) )   ! number of significant digits\n'
                elif name_var.startswith("so"):
                    if ":,:" in var: arg = var.replace(':,:','ji,jj')
                    else: arg = f"{var}(ji,jj)"
                    line+=f"{indent}DO_2D( 0, 0, 0, 0); nbdig2d(ji,jj) = real(nb_significant_digit({arg}), wp); END_2D\n"
                    line+= f'{indent}CALL histwrite( {list_vars[0]}, {list_vars[1].strip()[:-1]}_dig{list_vars[1].strip()[-1]}, kt, nbdig2d, 1, (/-1/) )   ! number of significant digits\n'
                else:
                    break
            break

        elif 'iom_put' in match.group(1): #special case for iom_put 
            var = list_vars[1].replace(' ','')
            name_var = list_vars[0].replace(' ','')[1:-1]

            if write_nb_significant_numbers:
                indent = line[:line.find(f'CALL iom_put')]
                if name_var in ['uoce', 'voce', 'toce', 'soce']:
                    if ":,:,:" in var: arg = var.replace(':,:,:','ji,jj,jk')
                    else: arg  = f"{var}(ji,jj,jk)"
                    line+=f"{indent}DO_3D( 0, 0, 0, 0, 1, jpk ); nbdig3d(ji,jj,jk) = {wp_st}(nb_significant_digit({arg}), nb_significant_digit({arg}), nb_significant_digit({arg})); END_3D\n"
                    nbdig = "nbdig3d"
                    line+= f'{indent}CALL iom_put( {list_vars[0].strip()[:-1]}_dig{list_vars[0].strip()[-1]}, {nbdig})   ! number of significant digits\n'
                else:
                    break
            break
        
        else:
            for j, var in enumerate(list_vars):

                for v in changed_vars:
                    v = re.escape(v)
                    v_pattern = re.compile(f"\\b{v}\\b(?!\\s*=)")
                    v_match = v_pattern.search(var)
                    v_start = 0

                    while v_match:

                        s, k = v_match.span()
                        s += v_start; k += v_start
                        nb_brackets = 0

                        if k<len(var)-1 and var[k] == '(': 
                            nb_brackets += 1
                            while k<len(var)-1 and nb_brackets > 0:
                                k+=1
                                if var[k] == '(': nb_brackets += 1
                                if var[k] == ')': nb_brackets -= 1
                            k+=1
                            
                        if f"%{v}" in var:
                            new_var = var[:k]+"%x"
                        elif (st_date and ("ju2ymds" in match.group() or "ymds2ju" in match.group()) and j==len(list_vars)-1) \
                            or 'xios_recv_field' in match.group().lower() or "nf90_get_" in match.group().lower():
                            v = var[:k]
                            new_var = v+"%x"
                            if "=" in v : v = v.split("=")[1]
                            vars_to_broadcast.append(v)
                        else:
                            new_var = var[:s] + f"(({var[s:k]}%x+{var[s:k]}%y+{var[s:k]}%z)/3.)"
                        
                        list_vars[j] = new_var+var[k:]

                        v_start = len(new_var)
                        var = list_vars[j]
                        v_match = v_pattern.search(var[v_start:]) # continue until no more variable to update

        l = line[:start]+','.join(list_vars)
        line, new_start = l+line[stop:], len(l)

        match = real_fcn_pattern.search(line[new_start:])

    if write_nb_significant_numbers and 'histdef(' in line :
        start = line.find('histdef(')+8
        list_vars, stop = split_args(line, start)
        name = list_vars[1].strip()[1:-1]
        if (name.startswith('vo') or name.startswith('so')): 
           line += line.replace(name,f'{name}_dig')+"\n"

    def min_max_nested(string, m):
        pattern = re.compile(r"\b(min|max)\b\s*\(", re.I)
        list_vars, stop = split_args(string, replace_blanks=True)
        for i, v in enumerate(list_vars):
            match = pattern.search(v)
            if match: 
                m = match.group(1)
                _, startv = match.span()
                new_v, stopv =  min_max_nested(v[startv:], m)
                list_vars[i] = v[:startv] + new_v + v[startv+stopv:]
        while len(list_vars)>2:
            v0 = f"{m}({list_vars[0]},{list_vars[1]})"
            list_vars = [v0] + list_vars[2:]

        new_string = ' ' +','.join(list_vars)
        return new_string, stop

    pattern = re.compile(r"\b(min|max)\b\s*\(", re.I)
    match = pattern.search(line)
    new_start = 0
    while match :
        m = match.group(1)
        _, start = match.span()
        start += new_start
        string = line[start:]
        new_string, stop = min_max_nested(string, m)
        l = line[:start] + new_string
        line, new_start = l + line[stop+start:], len(l)
        match = pattern.search(line[new_start:])

    # case of cmplx function

    match = cmplx_pattern.search(line)
    if match and not real_fcn_pattern.search(line):
        new_start = 0
        precision = None

        while match : 
            m = match.group(1)
            _, start = match.span()
            start += new_start

            list_vars, stop = split_args(line, start)

            if len(list_vars)>1 and precision_pattern.search(list_vars[-1]): 
                precision = list_vars[-1]
                list_vars = list_vars[:-1]
            
            l = line[:start]+','.join(list_vars)
            line, new_start = l+line[stop:], len(l)
            match = cmplx_pattern.search(line[new_start:])
        
        #this changes every pattern in the same way, works for now but to fix to avoid future bugs!
        if "cmplx" in m.lower() :  
            #if 'DDPDD' in line: line = cmplx_pattern.sub(f'complex_double_st(', line)  # force double prec for DDPDD
            if 'dp' in precision:
                line = cmplx_pattern.sub(f'complex_double_st(', line)
            elif 'sp' in precision:
                line = cmplx_pattern.sub(f'complex_single_st(', line)
            else:
                line = cmplx_pattern.sub(f'complex_{wp_st}(', line)

    # broadcast of namelist variables

    match = namelist_pattern.search(line)
    if  match : 
        nam = match.group(1)
        _, start = match.span()
        list_vars, stop = split_args(line, start, replace_blanks=True)
        dict_vars_namelist[nam] = list_vars

    for nam in dict_vars_namelist.keys() :

        if f"READ_NML_CFG(numnam,{nam})" in line or f"READ_NML_(numnam_cfg,cfg,{nam}" in line: 
            indent = line[:line.find("READ_NML_")]
            for var in dict_vars_namelist[nam]:
                if var in namelist_real_vars and var not in fixed_vars:
                    line+=f'{indent}{var} = {wp_st}({var}%x, {var}%x, {var}%x)\n'
                    changed_vars.add(var)

    for v in vars_to_broadcast : # broadcasting
        if 'present' in line.lower():
            line+=f'IF (PRESENT({v.split("(")[0]})) THEN; {v}%y = {v}%x; {v}%z = {v}%x; ENDIF \n'
        else:
            line+=f'{v}%y = {v}%x; {v}%z = {v}%x \n'

    lines[i] = line # finally, save modified line 

with open(f"{clean_dir}/{basename}.{extension}", "w") as f:
    f.writelines(lines)
