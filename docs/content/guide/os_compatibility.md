# OS compatibility

BundleWrap by necessity takes a pragmatic approach to supporting different operating systems and distributions. Our main target is Linux, but support for other UNIXes is also evolving. We cannot guarantee to be compatible with every distribution and BSD flavor under the sun, but we try to cover the common ones.

<br>

## node.os and node.os_version

You should set these attributes for every node. Giving BundleWrap this information allows us to adapt some built-in behavior.

<br>

## other node attributes

In some cases (e.g. when not using sudo) you will need to manually adjust some things. Check the docs [on node-level OS overrides](../repo/nodes.py.md#os-compatibility-overrides).
