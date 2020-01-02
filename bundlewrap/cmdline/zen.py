from ..utils.text import mark_for_translation as _
from ..utils.ui import io

ZEN = _("""
      ,
     @@
   @@@@
  @@@@@
  @@@@@
  @@@@@
  @@@@@
  @@@@@
  @@@@@                       '@@@@@@,          .@@@@@@+           +@@@@@@.
  @@@@@@,                  `@@@@@@@           +@@@@@@,          `@@@@@@#
  @@@@@@@@+              :@@@@@@'          `@@@@@@@           ;@@@@@@:
  @@@@@@@@@@@`         #@@@@@@.          :@@@@@@'           @@@@@@@`
  @@@@@ ;@@@@@@;    .@@@@@@#           #@@@@@@`          ,@@@@@@+
  @@@@@   `@@@@@@#'@@@@@@:          .@@@@@@+           +@@@@@@.
  @@@@@      +@@@@@@@@@           +@@@@@@,          `@@@@@@#
  @@@@@        ,@@@@@@+        `@@@@@@@@@`        ;@@@@@@:
  @@@@@           @@@@@@@`   :@@@@@@'@@@@@@'    @@@@@@@`
  @@@@@             ;@@@@@@#@@@@@@`   `@@@@@@@@@@@@@+
  @@@@@@@@@@@@@@@@@@@@@@@@@@@@@#         +@@@@@@@@.
  @@@@@@@@@@@@@@@@@@@@@@@@@@@,             .@@@#


  The Zen of BundleWrap
  ─────────────────────

  BundleWrap is a tool, not a solution.
  BundleWrap will not write your configuration for you.
  BundleWrap is Python all the way down.
  BundleWrap will adapt rather than grow.
  BundleWrap is the single point of truth.
""")

def bw_zen(repo, args):
    io.stdout(ZEN)
