# Run `pyinstaller pmca-gui.spec` to generate an executable

input = 'pmca-gui.py'
output = 'pmca-gui'
console = False

with open('build.spec') as f:
 exec(f.read())
