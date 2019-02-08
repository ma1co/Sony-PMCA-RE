# Run `pyinstaller pmca-console.spec` to generate an executable

input = 'pmca-console'
output = 'pmca-console'
console = True

with open('build.spec') as f:
 exec(f.read())
