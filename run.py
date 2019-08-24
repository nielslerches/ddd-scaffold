#!/usr/bin/env python

import argparse
import os
import re

from importlib import import_module


def main():
    parser = argparse.ArgumentParser()
    runners = []
    for name in os.listdir(os.path.abspath('./runners/')):
        name = re.sub(r'\.pyc?', '', name)
        if name.startswith('__') and name.endswith('__'):
            continue
        runners.append(name)

    parser.add_argument('runner', choices=runners)
    args = parser.parse_args()
    module = import_module('runners.{}'.format(args.runner))
    module.run()


if __name__ == '__main__':
    main()
