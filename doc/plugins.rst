=======
Plugins
=======

The plugin system in Blockwart is an easy way of integrating third-party code into your repository.

|

Finding plugins
###############

It's as easy as :command:`bw repo plugin search <term>`.

|

Installing plugins
##################

You probably guessed it: :command:`bw repo plugin install <plugin>`

Installing the first plugin in your repo will create a file called ``plugins.json``. You should commit this file (and any files installed by the plugin of course) to version control.

.. warning::
	Avoid editing files provided by plugins at all costs. Local modifications will prevent future updates to the plugin.

|

Updating plugins
################

You can update all installed plugins with this command: :command:`bw repo plugin update`

|

Removing a plugin
#################

:command:`bw repo plugin remove <plugin>`

|

Writing your own
################

.. seealso::

   :doc:`The guide on publishing your own plugins <dev_plugins>`
