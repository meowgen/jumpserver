import os
import compileall

current_dir = os.getcwd()
print(current_dir)

compileall.compile_dir(current_dir,legacy=True)
