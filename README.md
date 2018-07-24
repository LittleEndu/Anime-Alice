# Alice
<a href="https://discordbots.org/bot/354974625593032704" >
  <img src="https://discordbots.org/api/widget/servers/354974625593032704.svg?noavatar=true" alt="Alice" />
</a>
<a href="https://discordbots.org/bot/354974625593032704" >
  <img src="https://discordbots.org/api/widget/lib/354974625593032704.svg?noavatar=true" alt="Alice" />
</a>

Discord bot for linking anime and other otaku stuff

### Commands
Assuming you have ``!`` as your prefix

<> is required, () is optional

**Anime lookup**
* ``!anime search <query>`` - Searches Anilist for anime. ``search`` can be replaced with ``?``
* ``!anime lucky <query>`` - Searches Anilist for anime. Automatically picks the most popular. ``lucky`` can be replaced with ``!``
    * ``!anime`` - Shows the last anime you looked up
    * ``!manga`` - *Currently doesn't work*
    
**Manga lookup**
* ``!manga search <query>`` - Searches Anilist for manga. ``search`` can be replaced with ``?``
* ``!manga lucky <query>`` - Searches Anilist for manga. Automatically picks the most popular. ``lucky`` can be replaced with ``!``
    * ``!anime`` - *Currently doesn't work*
    * ``!manga`` - Shows the last manga you looked up
    
**Lookup aliases**
* ``!search <medium name> <query>`` - Uses the above lookups to perform a search
* ``!lucky <medium name> <query>`` - Uses the above lookups to perform a lucky search

**Prefixes**
* ``!setprefix <prefix>`` - sets the guild wide prefix. *You need to be administrator on the guild*
* ``!removeprefix (prefix)`` - removes a prefix. If none is specified, it asks what prefix to remove. *You need to be administrator on the guild*
* ``!prefixes`` - Lists current prefixes

**Informational**
* ``!latecy`` - Reports bot latency. This command has several aliases like ``!hello`` and ``!ping``
* ``!emojiinfo <:custom_emoji:>`` - Shows from what server some emoji is.
* ``!mutualservers`` - Shows what servers the user and Alice share.
* ``!whois <member>`` - Displays information about the given member.
  * ``!whois botowner`` - Display information about LittleEndu#0001.
  * ``!whois serverowner`` - Displays information about the server owner.
  * ``!whois me`` - Displays information about the user.
  * ``!whois you`` - Displays information about Alice#7756.
  
 ### Permissions
 Alice uses these permissions. Last permissions are optional.
 
 * *Read Messages* - To hear users
 * *Send Messages* - To respond to users
 * *Embed links* - To send embeds. They are used to display info in concise manner.
    * *Add reactions* - To send out reactions while user has to make a choice.
    * *Attach Files* - Currently unused. Feel free to deny this permission
    * *Use External Emoji* - Currently unused. Feel free to deny this permission