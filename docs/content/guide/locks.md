# Locking

BundleWrap's decentralized nature makes it necessary to coordinate actions between users of a shared repository. Locking is an important part of collaborating using BundleWrap.

## Hard locks

Since very early in the history of BundleWrap, what we call "hard locks" were used to prevent multiple users from using `bw apply` on the same node at the same time. When BundleWrap finds a hard lock on a node in interactive mode, it will display information about who acquired the lock (and when) and will ask whether to ignore the lock or abort the process. In non-interactive mode, the operation is always cancelled for the node in question unless `--force` is used.

## Soft locks

Many teams these days are using a workflow based on pull requests. A common problem here is that changes from a feature branch might already have been applied to a set of nodes, while the master branch is still lacking these changes. While the pull request is open and waiting for review, other users might rightly use the master branch to apply to all nodes, reverting changes made by the feature branch. This can be a major nuisance.

As of version 2.6.0, BundleWrap provides "soft locks" to prevent this. The author of a feature branch can now lock the node so only he or she can use `bw apply` on it:

<pre><code class="nohighlight">$ bw lock add node1
✓ node1  locked with ID B9JS (expires in 8h)</code></pre>

This will prevent all other users from changing any items on the node for the next 8 hours. BundleWrap will tell users apart by their [BW_IDENTITY](env.md#BW_IDENTITY). Now say someone else is reviewing the pull request and wants to use `bw apply`, while still keeping others out and the original author in. This can be done by simply locking the node *again* as the reviewer. Nodes can have many soft locks. Soft locks act as an exemption from a general ban on changing items that goes into effect as soon as one or more soft locks are present on the node. Of course, if no soft locks are present, anyone can change any item.

You can list all soft locks on a node with:

<pre><code class="nohighlight">$ bw lock show node1
i node1  ID    Created              Expires              User   Items  Comment
› node1  Y1KD  2016-05-25 21:30:25  2016-05-26 05:30:25  alice  *      locks are awesome
› node1  B9JS  2016-05-24 13:10:11  2016-05-27 08:10:11  bob    *      me too</code></pre>

Note that each lock is identified by a case-insensitive 4-character ID that can be used to remove the lock:

<pre><code class="nohighlight">$ bw lock remove node1 y1kd
✓ node1  lock Y1KD removed</code></pre>

Expired locks are automatically and silently purged whenever BundleWrap has the opportunity. Be sure to check out `bw lock add --help` for how to customize expiration time, add a short comment explaining the reason for the lock, or lock only certain items. Using `bw apply` on a soft locked node is not an error and affected items will simply be skipped.
