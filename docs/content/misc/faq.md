# FAQ

## Technical

### BundleWrap says an item failed to apply, what do I do now?

Try running `bw apply -i nodename` to see which attribute of the item could not be fixed. If that doesn't tell you enough, try `bw --debug apply -i nodename` and look for the command BundleWrap is using to fix the item in question. Then try running that command yourself and check for any errors.

<br>

### What happens when two people start applying configuration to the same node?

BundleWrap uses a [locking mechanism](../guide/locks.md) to prevent collisions like this.

<br>

### How can I have BundleWrap reload my services after config changes?

See [canned actions](../repo/items.py.md#canned_actions) and [triggers](../repo/items.py.md#triggers).

<br>

### Will BundleWrap keep track of package updates?

No. BundleWrap will only care about whether a package is installed or not. Updates will have to be installed through a separate mechanism (I like to create an [action](../items/action.md) with the `interactive` attribute set to `True`). Selecting specific versions should be done through your package manager.

<br>

### Is there a probing mechanism like Ohai?

No. BundleWrap is meant to be very push-focused. The node should not have any say in what configuration it will receive.

<br>

### Is BundleWrap secure?

BundleWrap is more concerned with safety than security. Due to its design, it is possible for your coworkers to introduce malicious code into a BundleWrap repository that could compromise your machine. You should only use trusted repositories and code. We also recommend following commit logs to your repos.

<br>

## The BundleWrap Project

### Why doesn't BundleWrap provide pre-built community bundles?

In our experience, bundles for even the most common pieces of software always contain some opinionated bits specific to local infrastructure. Making bundles truly universal (e.g. in terms of supported Linux distributions) would mean a lot of bloat. And since local modifications are hard to reconcile with an upstream community repository, bundles would have to be very feature-complete to be useful to the majority of users, increasing bloat even more.

Maintaining bundles and thus configuration for different pieces of software is therefore out of scope for the BundleWrap project. While it might seem tedious when you're getting started, with some practice, writing your own bundles will become both easy and precise in terms of infrastructure fit.

<br>

### Why do contributors have to sign a Copyright Assignment Agreement?

While it sounds scary, Copyright assignment is used to improve the enforceability of the GPL. Even the FSF does it, [read their explanation why](http://www.gnu.org/licenses/why-assign.html). The agreement used by BundleWrap is from [harmonyagreements.org](http://harmonyagreements.org).

If you're still concerned, please do not hesitate to contact [@trehn](https://twitter.com/trehn).
