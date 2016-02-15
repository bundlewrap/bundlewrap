# Plugins

The plugin system in BundleWrap is an easy way of integrating third-party code into your repository.

<div class="alert alert-warning">While plugins are subject to some superficial code review by BundleWrap developers before being accepted, we cannot make any guarantees as to the quality and trustworthiness of plugins. Always do your due diligence before running third-party code.</div>

<br>

## Finding plugins

It's as easy as `bw repo plugin search <term>`. Or you can browse [plugins.bundlewrap.org](http://plugins.bundlewrap.org).

<br>

## Installing plugins

You probably guessed it: `bw repo plugin install <plugin>`

Installing the first plugin in your repo will create a file called `plugins.json`. You should commit this file (and any files installed by the plugin of course) to version control.

<div class="alert alert-info">Avoid editing files provided by plugins at all costs. Local modifications will prevent future updates to the plugin.</div>

<br>

## Updating plugins

You can update all installed plugins with this command: `bw repo plugin update`

<br>

## Removing a plugin

`bw repo plugin remove <plugin>`

<br>

## Writing your own

See the [guide on publishing your own plugins](../guide/dev_plugin.md).
