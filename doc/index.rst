.. mge_downloader documentation master file, created by
   sphinx-quickstart on Wed Sep  2 08:03:56 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

mge_downloader documentation!
==========================================
Uploads FASTA files to https://cge.cbs.dtu.dk/services/MobileElementFinder/ and downloads the results.
Uploads are staggered in order to prevent overloading of the server. Results are fetched after a certain
wait time. The system uses Selenium, a browser control system. I chose this system as the uploads on the
MEFinder website rely on Javascript queries and can easily be controlled with Selenium.
All of this could probably be optimized. However, because only a few instances are run a the same time
and the program is waiting most of the run-time, this would offer little advantage.

**Please adhere to the minimum time between requests in order to no overload the server.**

Workflow
===========

.. graphviz::


   digraph Waterfall {

       subgraph cluster_0 {
           node [shape=box]
           color=red
           label="FASTA #1"
           "No Delay" -> "Upload 1"  -> "Wait" -> "Download Result 1";
       }

       subgraph cluster_1 {
           node [shape=box]
           color=blue
           label="FASTA #2"
           "Delay" -> "Upload 2" -> "Wait " -> "Download Result 2";
       }


       subgraph cluster_2 {
           node [shape=box]
           color=green
           label="FASTA #3"
           "Delay " -> "Upload 3" -> " Wait " -> "Download Result 3";
       }

       subgraph cluster_3 {
           node [shape=box]
           "Delay  " -> "Upload(n)"  -> "..." -> "... ";
           label = "FASTA(n)";
           color=gray
       }


     edge[weight=0.1]
     #edge [style=invis, weight=0.1];
     #"No Delay"-> "Delay"
     #"Delay" -> "Delay "
     #"Delay " -> "Delay  "
     "Upload 1" -> "Delay"
     "Upload 2" -> "Delay "
     "Upload 3" -> "Delay  "
   }



Quick Usage
===========================================

Upload all fasta files from current directory and download results:

.. code-block:: bash

    $ python mge_downloader --outdir outdir *.fna


Detailed Usage
==================================

.. code-block:: bash

   $ python main.py --help
   ================= mgefinder 0.1.0 =================
   usage: main.py [-h] --outdir directory [--time-to-next minutes] [--time-to-fetch-result minutes] fasta files) [fasta file(s ...]

   Upload fasta file to mefinder and download results.

   positional arguments:
     fasta file(s)         fastA files.

   optional arguments:
     -h, --help            show this help message and exit
     --outdir directory    directory that should be used to place the output.
     --time-to-next minutes
                           Number of minutes to wait before sending next fasta file
     --time-to-fetch-result minutes
                           Number of minutes to wait before fetching the result

   Example: python mge_downloader.py --outdir dir1 *.fna


Defaults
############

* --time-to-next minutes: 5 min
* --time-to-fetch-result minutes: 30 min



Minimum values
################

* --time-to-next minutes: 5 min
* --time-to-fetch-result minutes: 5 min




Installation
===========================================
Windows
###########################################
You will need to install Chrome, Chromedriver and Selenium

* Install Chrome from https://www.google.com/chrome/
* Install Chromedriver from https://sites.google.com/a/chromium.org/chromedriver/downloads
* Install Python (3.7+) from https://www.python.org/downloads/
* Install Selenium bindings through the command line

.. code-block:: bash

    > pip install selenium


Linux
####################
Ubuntu
---------
You will need to install Chrome, Chromedriver and Selenium.

Follow these instructions: https://gist.github.com/ziadoz/3e8ab7e944d02fe872c3454d17af31a5

ARCH
------------
You will need to install Chrome, Chromedriver and Selenium.

.. code-block:: bash

  $ sudo pacman -Syu
  $ sudo pacman -S chromium python python-selenium

Chromedriver can be installed through the AUR using `yay`

.. code-block:: bash

  $ sudo pacman -S yay
  $ yay -Syu
  $ yay -S chromedriver




.. toctree::
   :maxdepth: 2
   :caption: Contents:



Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
