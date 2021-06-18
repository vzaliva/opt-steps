#!/usr/bin/env python

import os
import io
import re
import sys
import subprocess
import click
import difflib

import diff2HtmlCompare

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

class CodeDiffOptions(object):
    verbose = False
    syntax_css = "vs"
    print_width = None

# Generate side-by-side comparison
def mkcmp(file1, file2, outputpath):
    codeDiff = diff2HtmlCompare.CodeDiff(file1, file2, name=file2)
    options = CodeDiffOptions()
    codeDiff.format(options)
    codeDiff.write(outputpath)


# Generate context diff
def mkdiff(file1, file2, outputpath):
    with open(file1, 'r') as fh:
        l1 = fh.readlines()
    with open(file2, 'r') as fh:
        l2 = fh.readlines()
    hdiff = difflib.HtmlDiff(wrapcolumn=80).make_file(l1,l2,file1,file2,context=True,numlines=5)
    with io.open(outputpath, 'w') as fh:
        fh.writelines(hdiff)

INDEX_HTML = """
<!DOCTYPE html>
<html class="no-js">
    <head>
        <meta charset="utf-8">
        <title>
            %(html_title)s
        </title>
        <meta name="description" content="">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="mobile-web-app-capable" content="yes">
    </head>
    <body>
        <table>
            <tr>
            <th>File</th>
            <th>Side-by-side</th>
            <th>Compact Diff</th>
            <th>Description</th>
            </tr>
            %(table_rows)s
        </table>
  </tr>
    </body>
    </html>
"""

def flink(s):
    if s is None:
        return("")
    else:
        n = os.path.basename(s)
        return('<a href="%s"> %s</a>' % (n,n))

def mkindex(cname, iname, l):
    rows_html = ["<tr><td>%s</td> <td>%s</td><td>%s</td><td><i>%s</i></td> </tr>" % (flink(f),flink(c),flink(d),ds) for (f,c,d,ds) in l]
    html_params = {
            "html_title": ("LLVM optimization steps for %s" % cname),
             "table_rows" : "\n".join(rows_html)
        }
    
    html = INDEX_HTML % html_params
    with io.open(iname, 'w') as fh:
        fh.write(html)
    
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
    res = [(llname, None, None, "Original file")]
    for (pn,ps) in passes:
        pname = "%s.%d.ll" % (name,pn)
        print("[%d/%d] %s" % (pn, ptotal, ps))
        subprocess.check_call(['opt', OPTFLAG, ("-opt-bisect-limit="+str(pn)), '-S', llname, '-o', pname], stderr=subprocess.DEVNULL)
        result = subprocess.run(['cmp', '-s', prev, pname],stdout=subprocess.DEVNULL)
        if result.returncode == 0:
            print("\t unchanged")
            os.remove(pname)
        else:
            print("\t %s generated" % pname)
            dname = "%s.%d.diff.html" % (name,pn)
            mkdiff(prev,pname,dname)
            cmpname = "%s.%d.cmp.html" % (name,pn)
            mkcmp(prev,pname,cmpname)
            res.append((pname, cmpname, dname, ps))
            prev = pname
    iname = "%s.html" % name
    mkindex(cname, iname, res)
    
if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    main()

