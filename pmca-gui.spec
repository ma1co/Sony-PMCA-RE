# Run `pyinstaller pmca-gui.spec` to generate an executable

input = 'pmca-gui.py'
output = 'pmca-gui'
console = False

execfile('build.spec')
