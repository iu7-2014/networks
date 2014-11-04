import sys
import os

destop_file = os.path.expanduser('~/Desktop/')
program = sys.argv[1]
program_dir = os.path.join(sys.argv[2], 'rc/' + program)
filename = {'server': 'server.py', 'client': 'start.py'}[program]
title = {'server': 'RC сервер', 'client': 'RC клиент'}[program]

desktop = """#!/usr/bin/env xdg-open
[Desktop Entry]
Type=Application
Name={title}
Exec=/bin/sh -c "cd {working_dir}; python3 {filename}"
Icon=network-server
Categories=Application;
""".format(working_dir=program_dir, filename=filename, title=title)
with open(destop_file + title, 'w') as f:
    f.write(desktop)
