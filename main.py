"""Compatibility launcher for python main.py."""
import runpy

if __name__ == '__main__':
    runpy.run_module('app', run_name='__main__')
