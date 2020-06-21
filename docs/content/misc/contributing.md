# Contributing

We welcome all input and contributions to BundleWrap. If you've never done this sort of thing before, maybe check out [contribution-guide.org](http://www.contribution-guide.org). But don't be afraid to make mistakes, nobody expects your first contribution to be perfect. We'll gladly help you out.

<br>

## Submitting bug reports

Please use the [GitHub issue tracker](https://github.com/bundlewrap/bundlewrap/issues) and take a few minutes to look for existing reports of the same problem (open or closed!).

<div class="alert alert-danger">If you've found a security issue or are not at all sure, just contact <a href="mailto:trehn@bundlewrap.org">trehn@bundlewrap.org</a>.</div>

<br>

## Contributing code

<div class="alert alert-info">Before working on new features, try reaching out to one of the core authors first. We are very concerned with keeping BundleWrap lean and not introducing bloat.</div>

Here are the steps:

1. Write your code. Awesome!
2. If you haven't already done so, please consider writing tests. Otherwise, someone else will have to do it for you.
3. Same goes for documentation.
4. Set up a [virtualenv](http://virtualenv.readthedocs.org/en/latest/) and run `pip install -r requirements.txt`.
5. Make sure you can connect to your localhost via `ssh` without using a password and that you are able to run `sudo`.
6. Run `py.test tests/`.
7. Review and sign the Copyright Assignment Agreement (CAA) by adding your name and email to the `AUTHORS` file. (This step can be skipped if your contribution is too small to be considered intellectual property, e.g. spelling fixes)
8. Open a pull request on [GitHub](https://github.com/bundlewrap/bundlewrap).
9. Feel great. Thank you.

<br>

## Contributing documentation

The process is essentially the same as detailed above for code contributions. You will find the docs in `docs/content/` and can preview them using `cd docs && mkdocs serve`.

<br>

## Help

If at any point you need help or are not sure what to do, just drop by in [#bundlewrap on Freenode](irc://chat.freenode.net/bundlewrap) or poke [@bundlewrap on Twitter](https://twitter.com/bundlewrap).
