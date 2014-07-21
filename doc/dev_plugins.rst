========================
Writing your own plugins
========================

:doc:`Plugins <plugins>` can provide almost any file in a BundleWrap repository: bundles, custom items, hooks, libs, etc.

Notable exceptions are :file:`nodes.py` and :file:`groups.py`. If your plugin wants to extend those, use a :doc:`lib <libs>` instead and ask users to add the result of a function call in your lib to their nodes or groups dicts.

.. warning::

	If your plugin depends on other libraries, make sure that it catches ImportErrors in a way that makes it obvious for the user what's missing. Keep in mind that people will often just :command:`git pull` their repo and not install your plugin themselves.

|

Starting a new plugin
#####################

**Step 1: Clone the plugins repo**

Create a clone of the `official plugins repo <https://github.com/bundlewrap/plugins>`_ on GitHub.

**Step 2: Create a branch**

You should work on a branch specific to your plugin.

**Step 3: Copy your plugin files**

Now take the files that make up your plugin and move them into a subfolder of the plugins repo. The subfolder must be named like your plugin.

**Step 4: Create required files**

In your plugin subfolder, create a file called :file:`manifest.json` from this template:

.. code-block:: json

	{
		"desc": "Concise description (keep it somewhere around 80 characters)",
		"help": "Optional verbose help text to be displayed after installing. May\ninclude\nnewlines.",
		"provides": [
			"bundles/example/bundle.py",
			"hooks/example.py"
		],
		"version": 1
	}

The ``provides`` section must contain a list of all files provided by your plugin.

You also have to create an :file:`AUTHORS` file containing your name and email address.

Last but not least we require a :file:`LICENSE` file with an OSI-approved Free Software license.

**Step 5: Update the plugin index**

Run the :file:`update_index.py` script at the root of the plugins repo.

**Step 6: Run tests**

Run the :file:`test.py` script at the root of the plugins repo. It will tell you if there is anything wrong with your plugin.

**Step 7: Commit**

Commit all changes to your branch

**Step 8: Create pull request**

Create a pull request on GitHub to request inclusion of your new plugin in the official repo. Only then will your plugin become available to be installed by :command:`bw repo plugin install yourplugin`.

|

Updating an existing plugin
###########################

To release a new version of your plugin:

* Increase the version number in :file:`manifest.json`
* Update the list of provided files in :file:`manifest.json`
* If you're updating someone elses plugin, you should get their consent and add your name to :file:`AUTHORS`

Then just follow the instructions above from step 5 onward.
