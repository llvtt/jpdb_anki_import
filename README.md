## Issues

* Deal with importing history for J=>E and E=>J separately
* Import custom metadata set on JPDB cards (probably not possible without API)
--> custom sentence
--> custom definition
--> enabled definitions on reverse side
* Manual for how to add audio, sentences, rich media
* Filter import by what is in a specific JPDB deck, e.g. only N3, etc.


## Creating Rich Cards

1. Install this plugin and import your JPDB review history using the "Basic" note type.
   These notes only have two fields, `Front` and `Back`. Leave that for now.

2. Install [Japanese Example Sentences](https://ankiweb.net/shared/info/2413435972) plugin.
   Go to the plugin configuration, and change these settings:

       * `srcFields`: set this to "Front" and "Back"
       * `noteTypes`: set this to "Basic"
       * `combinedDstField`: set this to "examples"
       * `lookupOnAdd`: set this to `false` (optional, I just want to
         seed some examples to start, then take over adding examples
         manually from there)

3. Add a `examples` field to the `Basic` note type, which will hold example sentences.

4. Restart Anki. Select all cards in the browser and and "Bulk-add Examples"

5. Install and use AwesomeTTS

6. Install and use pitch diagram builder
