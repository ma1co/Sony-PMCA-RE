# Run `pyinstaller pmca-gui.spec` to generate an executable

input = 'pmca-gui'
output = 'pmca-gui'
console = False

with open('build.spec') as f:
 exec(f.read())
