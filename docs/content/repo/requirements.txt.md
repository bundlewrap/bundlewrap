<style>.bs-sidebar { display: none; }</style>

# requirements.txt

This optional file can be used to ensure minimum required versions of BundleWrap and other Python packages on every machine that uses a repository.

`bw repo create` will initially add your current version of BundleWrap:

<pre><code class="nohighlight">bundlewrap>=2.4.0</code></pre>

You can add more packages as you like (you do not have to specify a version for each one), just append each package in a separate line. When someone then tries to use your repo without one of those packages, BundleWrap will exit early with a friendly error message:

<pre><code class="nohighlight">! Python package 'foo' is listed in requirements.txt, but wasn't found. You probably have to install it with `pip install foo`.</code></pre>
