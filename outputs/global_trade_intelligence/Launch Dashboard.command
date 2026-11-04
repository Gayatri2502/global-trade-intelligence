#!/bin/zsh
cd "${0:A:h}"
trade_python=/Users/alphacentauric/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
if [[ ! -x "$trade_python" ]]; then trade_python=$(command -v python3); fi
exec "$trade_python" server.py --open
