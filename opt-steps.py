#!/usr/bin/env python

import os
import re
import sys
import subprocess
import click

OPTFLAG='-O3'

def get_passes(llname):
    p = subprocess.check_output(['opt', OPTFLAG, '-opt-bisect-limit=-1', '-S', llname, '-o', '/dev/null'], stderr=subprocess.STDOUT, text=True)
    pl = list(map(str.strip, p.split('\n')))
    res = []
    for s in pl:
        m = re.match(r"""BISECT: running pass \((\d+)\) (.*)""", s)
        if not m is None:
            res.append((int(m.group(1)), m.group(2)))
    res.sort(key = lambda x: x[0])
    return(res)

@click.command()
@click.version_option("1.0")
@click.option('--verbose', '-v', is_flag=True, help='Enables verbose mode.')
@click.argument('cname')
def main(verbose, cname):
    if not cname.endswith(".c"):
        print("Argument %s must have .c extension" % cname)
        sys.exit(1)
    if not os.path.exists(cname):
        print("File %s does not exist" % cname)
        sys.exit(1)
    
    name = cname[:-2]
    llname = name + '.ll'
    # Generate LL file
    subprocess.check_call(['clang', '-emit-llvm', '-S', '-O0', cname, '-o', llname])

    passes = get_passes(llname)
    prev = llname
    ptotal = len(passes)
    for (pn,ps) in passes:
        pname = "%s.%d.ll" % (name,pn)
        print("[%d/%d] Generating %s: %s" % (pn,ptotal,pname,ps))
        subprocess.check_call(['opt', OPTFLAG, ("-opt-bisect-limit="+str(pn)), '-S', llname, '-o', pname], stderr=subprocess.DEVNULL)
        result = subprocess.run(['cmp', '-s', prev, pname], stdout=subprocess.DEVNULL)
        if result.returncode == 0:
            print("\t unchanged")
            os.remove(pname)
        else:
            print("\t CHANGED")
            prev = pname

    
if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    main()
