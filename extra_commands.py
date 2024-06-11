# Your necessary imports go here (if the import isn't already installed, make sure to add them to "requirements_extra.txt")


def add_commands(bot, variables={}):
    """
    Your commands go here, add them as you would normally add a command (check the main file).
    You can parse variables from the main file, for example if you want to parse the "EMBED_COLOR" variable,
    then variables={'EMBED_COLOR': EMBED_COLOR}.
    You can also override some stuff, like the "on_ready" event for example:

    @bot.event
    async def on_ready():
        print('The bot is ready!')
    """
    globals().update(variables)

