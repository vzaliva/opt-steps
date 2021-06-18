#!/bin/sh
rsync -avz --exclude=.git samples/ www.crocodile.org:~/www/tmp/llvm

