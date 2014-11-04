import sys
import os

destop_file = os.path.expanduser('~/Desktop/')
program = sys.argv[1]
program_dir = os.path.join(sys.argv[2], 'rc/' + program)
d = {'server': 'server.py', 'client': 'start.py'}

desktop = """#!/usr/bin/env xdg-open
[Desktop Entry]
Type=Application
Name=RC Client
Exec=/bin/sh -c "cd {working_dir}; python3 {program}"
Icon=network-server
Categories=Application;
""".format(working_dir=program_dir, program=d[program])
with open(destop_file + 'RC ' + program, 'w') as f:
    f.write(desktop)
