INSTALL:
========
1. Download TorBrowser for linux: https://www.torproject.org/download/
2. Do the setup as explained here: https://vasilian.net/tor.html
3. Start browser
4. Go to web.whatsapp.com
5. Scan the QR Code with the telephone where the bot will be installed
4. F12 -> Console
5. Copy bot js code and paste it into console + <enter>
6. Done

DEBUG:
======
1. The robot code is below the line:  "--- WhatsApp Web Chat ---"
2. Prepare the code for debugging.
   var debugging = true;
   var debug_phone = "4915711145226";

   "debugging" boolean will allow replies only to debug_phone number.
   "debug_phone" number is a second phone that you have and can test with.

3. Copy-paste bot text into console + <enter>
4. Send few messages from "debug_phone" to the bot number for testing.

PATCH WAPI:
===========
1. Yearly whatsapp will run updates to their service which will break the WAPI.
2. Go to https://github.com/mukulhase/WebWhatsapp-Wrapper/blob/master/webwhatsapi/js/wapi.js
3. Read the pull requests
4. Merge any change you think may fix the WAPI break and test.
