#!/usr/bin/env python

"""
Add Dash docs anchor tags to html source.
"""

import argparse
import os
import re
import sys
import urllib

parser = argparse.ArgumentParser()
parser.add_argument('filename',
                    help=('The file to add dash doc anchors to.'))
parser.add_argument('-v', '--verbose',
                    dest='verbose',
                    action='store_true')
args = parser.parse_args()

if not os.path.isfile(args.filename):
    print 'Error: File %s does not exist' % args.path
    sys.exit

html = open(args.filename).read()

# Use regex to add dash docs anchors
def dashrepl(match):
    (hopen, id, name, hclose) = match.group(1, 2, 3, 4)

    dashname = name
    dashname = re.sub('<.*?>', '', dashname)
    dashname = re.sub('[^a-zA-Z0-9\.\(\)\?\',:; ]', '-', dashname)
    dashname = urllib.quote(dashname)

    dash = ('<a name="//apple_ref/cpp/Section/%s" class="dashAnchor"></a>' %
            (dashname))
    header = '<h%s id="%s">%s</h%s>' % (hopen, id, name, hclose)
    return "%s\n%s" % (dash, header)

html = re.sub('<h([1-2]) id="(.*?)">(.*?)</h([1-2])>', dashrepl, html)

with open(args.filename, 'w') as f:
    f.write(html)

if args.verbose:
    print 'Added dash docs anchors to %s' % args.filename

