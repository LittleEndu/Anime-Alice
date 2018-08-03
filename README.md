# Alice
<a href="https://discordbots.org/bot/354974625593032704" >
  <img src="https://discordbots.org/api/widget/servers/354974625593032704.svg?noavatar=true" alt="Alice" />
</a>
<a href="https://discordbots.org/bot/354974625593032704" >
  <img src="https://discordbots.org/api/widget/lib/354974625593032704.svg?noavatar=true" alt="Alice" />
</a>

Discord bot for linking anime and other otaku stuff

## Commands
Assuming you have ``!`` as your prefix

<> is required, () is optional, ? will be asked if not provided


#### Anime commands

Allowed result types are ``anime``, ``manga``, and ``character``.
To make sure it works, please use the commands in all lowercase.

* ``!search <result type> <?query>`` - Searches Anilist for that result type.
* ``!luckysearch <result type> <?query>`` - Automatically returns the most popular result.
* ``!<result type> <query>`` - Shortcut for the search command. Note that these shortcuts don't ask for a query if not provided
* ``!!<result type> <query>`` - Shortcut for the lucky command. Note that the command name starts with ``!`` so the correct usage is ``<prefix>!<result type> <query>``

These extra commands are available based on what was your last result:
* Anime
  * ``!anime`` - Will show the last result
  * ``!manga`` - *Currently doesn't work*
  * ``!character`` - Searches for the characters in the anime
* Manga
  * ``!anime`` - *Currently doesn't work*
  * ``!manga`` - Will show the last result
  * ``!character`` - *Currently doesn't work*
* Character
  * ``!anime`` - *Currently doesn't work*
  * ``!manga`` - *Currently doesn't work*
  * ``!character`` - Will show the last result

#### Prefix commands
* ``!setprefix <prefix>`` - Sets the guild wide prefix. *You need to be administrator on the guild*
* ``!removeprefix <?prefix>`` - Removes a prefix. *You need to be administrator on the guild*
* ``!prefixes`` - Lists current prefixes

#### Informational commands
* ``!latecy`` - Reports bot latency. This command has several aliases like ``!hello`` and ``!ping``
* ``!emojiinfo <:custom_emoji:>`` - Shows from what server some emoji is.
* ``!mutualservers`` - Shows what servers the user and Alice share.
* ``!permissionsfor <member>`` - Shows the server permissions for some member.
* ``!permissionsin <channel> <member>`` - Shows the effective permissions for some member in some channel.
* ``!whois <member>`` - Displays information about the given member.
  * ``!whois botowner`` - Display information about LittleEndu#0001.
  * ``!whois serverowner`` - Displays information about the server owner.
  * ``!whois me`` - Displays information about the user.
  * ``!whois you`` - Displays information about Alice#7756.
  
 ## Permissions
 Alice uses these permissions. Last permissions are optional.
 
 * *Read Messages* - To hear users
 * *Send Messages* - To respond to users
 * *Embed links* - To send embeds. They are used to display info in concise manner.
    * *Add reactions* - To send out reactions while user has to make a choice.
    * *Manage messages* - Used to delete messages/reactions while user has to make a choice.
    * *Attach Files* - Currently unused. Feel free to deny this permission
    * *Use External Emoji* - Currently unused. Feel free to deny this permission