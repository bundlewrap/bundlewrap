# Writing your own plugins

[Plugins](../repo/plugins.md) can provide almost any file in a BundleWrap repository: bundles, custom items, hooks, libs, etc.

Notable exceptions are `nodes.py` and `groups.py`. If your plugin wants to extend those, use a [lib](../repo/libs.md) instead and ask users to add the result of a function call in your lib to their nodes or groups dicts.

<div class="alert alert-warning">If your plugin depends on other libraries, make sure that it catches ImportErrors in a way that makes it obvious for the user what's missing. Keep in mind that people will often just <code>git pull</code> their repo and not install your plugin themselves.</div>

<br>

## Starting a new plugin

### Step 1: Clone the plugins repo

Create a clone of the [official plugins repo](https://github.com/bundlewrap/plugins) on GitHub.

### Step 2: Create a branch

You should work on a branch specific to your plugin.

### Step 3: Copy your plugin files

Now take the files that make up your plugin and move them into a subfolder of the plugins repo. The subfolder must be named like your plugin.

### Step 4: Create required files

In your plugin subfolder, create a file called `manifest.json` from this template:

	{
		"desc": "Concise description (keep it somewhere around 80 characters)",
		"help": "Optional verbose help text to be displayed after installing. May\ninclude\nnewlines.",
		"provides": [
			"bundles/example/items.py",
			"hooks/example.py"
		],
		"version": 1
	}

The `provides` section must contain a list of all files provided by your plugin.

You also have to create an `AUTHORS` file containing your name and email address.

Last but not least we require a `LICENSE` file with an OSI-approved Free Software license.

### Step 5: Update the plugin index

Run the `update_index.py` script at the root of the plugins repo.

### Step 6: Run tests

Run the `test.py` script at the root of the plugins repo. It will tell you if there is anything wrong with your plugin.

### Step 7: Commit

Commit all changes to your branch

### Step 8: Create pull request

Create a pull request on GitHub to request inclusion of your new plugin in the official repo. Only then will your plugin become available to be installed by :command:`bw repo plugin install yourplugin`.

<br>

## Updating an existing plugin

To release a new version of your plugin:

* Increase the version number in `manifest.json`
* Update the list of provided files in `manifest.json`
* If you're updating someone elses plugin, you should get their consent and add your name to `AUTHORS`

Then just follow the instructions above from step 5 onward.
