# Run `pyinstaller pmca-console.spec` to generate an executable

input = 'pmca-console.py'
output = 'pmca-console'
console = True

execfile('build.spec')
