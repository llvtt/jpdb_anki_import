# jpdb_anki_import

## Overview

An Anki plugin that imports review history for words studied in [JPDB](https://jpdb.io). Currently working as of Anki 2.60.0.

This plugin imports the following information:
* Japanese spelling (e.g. 言葉)
* Japanese reading (e.g. ことば)
* Review history, accomplished by simulating the same button answer responses in Anki.

This plugin *does not* import:
* English definitions
* Custom sentences
* Audio
* Pitch accent

These data are not included in the JPDB review history export, so they are not included.
If/when JPDB has a public API, I will look into adding support, but for now this plugin 
is meant to create a good starting point in Anki for studying words previously added to JPDB,
so that other richer media (e.g. pictures, video, etc) can be added later.
See the "Recommended Additional Plugins" section below for links to some other Anki add-ons that can help
make the resulting cards richer with little effort.

## Usage

1. Download your JPDB review history by going to the [settings page](https://jpdb.io/settings) and clicking
   "Export vocabulary reviews (.json)" near the bottom of the page.
2. Create a new Anki deck where you want to import your JPDB cards.
3. After installing this add-on, in Anki, go to "Tools" => "Import from JPDB"
4. Follow the instructions in the setup window.

## Building
To build the package, run `python3 build.py` in the command line which will generate the add-on file `jpdb_anki_import.ankiaddon`.

### Testing
To test the file in Anki, perform the following steps:

1. Open Anki and click on "Tools" in the top menu bar.
2. Select "Add-ons" from the dropdown menu.
3. Click on "Install from file..."
4. Navigate to the directory where the jpdb_anki_import.ankiaddon file was generated, and select it.
5. Click "Open" to install the addon.
6. Restart Anki if prompted to do so.

## Recommended Additional Plugins

The following other Anki plugins can help flesh out cards created after the import to add translation and more detail:

* [Automatic Japanese Dictionary Lookup](https://ankiweb.net/shared/info/1015321168) adds English definitions for Japanese words
* [Japanese Example Sentences](https://ankiweb.net/shared/info/2413435972) adds example Japanese sentences.
* [AwesomeTTS](https://ankiweb.net/shared/info/1436550454) adds Japanese audio for words.
* [Japanese Pitch Accent](https://ankiweb.net/shared/info/148002038) adds pitch accent diagrams.
