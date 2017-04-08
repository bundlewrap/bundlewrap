#!/usr/bin/env python

"""
Reads an MkDocs YAML file and generates a Docset SQLite3 index from the
contents.
"""

import argparse
import os
import re
import sqlite3
import sys

import yaml
import types

parser = argparse.ArgumentParser()
parser.add_argument('yaml',
                    help=('The MkDocs YAML file to convert to a SQLite DB'))
parser.add_argument('sqlite',
                    help=('The SQLite DB file to create'))
parser.add_argument('-v', '--verbose',
                    dest='verbose',
                    action='store_true')
args = parser.parse_args()

if not os.path.isfile(args.yaml):
    print 'Error: Directory %s does not exist' % args.path
    sys.exit

# Set up db
db = sqlite3.connect(args.sqlite)
cur = db.cursor()

cur.execute('''
    DROP TABLE IF EXISTS searchIndex;
''')

cur.execute('''
    CREATE TABLE
        searchIndex(id INTEGER PRIMARY KEY,
                    name TEXT,
                    type TEXT,
                    path TEXT);
''')

cur.execute('''
    CREATE UNIQUE INDEX
        anchor
    ON
        searchIndex (name, type, path);
''')

db.commit()

# Read YAML and iterate over entries
with open(args.yaml) as f:
    rawyaml = f.read()


def parse_submenu(parent, subtree):
    for page in subtree:
        title = page.keys()[0]
        mdpath = page[title]

        if isinstance(mdpath, types.ListType):
            parse_submenu(title, mdpath)
        else:
            if '**HIDDEN**' not in title:
                if 'index.md' in mdpath:
                    htmlpath = mdpath.replace('index.md', 'index.html')
                else:
                    htmlpath = mdpath.replace('.md', '/index.html')

                if title == "<i class=\"fa fa-home\"></i>":
                    title = "home"

                if parent != '':
                    title = "%s - %s"%(parent, title)

                type = 'Guide'
                if parent == 'Items':
                    type = 'Builtin'

                cur.execute('''
                    INSERT OR IGNORE INTO
                        searchIndex(name, type, path)
                    VALUES
                        (?, ?, ?);
                ''', (title, type, htmlpath))

                db.commit()

                if args.verbose:
                    print "Added the following entry to %s:" % args.sqlite
                    print "    name: %s" % title
                    print "    type: %s" % type
                    print "    path: %s" % htmlpath
                    print


if rawyaml:
    prevtitle = ''
    parse_submenu(prevtitle, yaml.load(rawyaml).get('pages'))

db.close()

