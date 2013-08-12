
import logging
__sentinel = object()
def make_config_property(field, getter=None, setter=None, default=__sentinel):
    def fget(self):
        if default != __sentinel:
            if field in self.config_section:
                value = self.config_section[field]
            else:
                value = default()
        else:
            value = self.config_section[field]
        if getter is not None: value = getter(self, value)
        return value
    def fset(self, value):
        if setter is not None:
            value = setter(value)
        self.config_section[field] = value
    return property(fget, fset)


class BotModule(object):
    def __init__(self, config_section, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.apply_config(config_section)
        self.bot_instance = None

    def add_bot_instance(self, bot_instance):
        if self.bot_instance:
            return False
        self.bot_instance = bot_instance
        self.on_add_bot_instance(bot_instance)
        return True

    def remove_bot_instance(self, bot_instance):
        if bot_instance != self.bot_instance:
            raise ValueError("Can't remove bot_instance because this plugin wasn't registered for this bot")
        self.bot_instance = None
        self.on_remove_bot_instance(bot_instance)

    def on_add_bot_instance(self, bot_instance):
        pass

    def on_remove_bot_instance(self, bot_instance):
        pass

    def shutdown(self):
        ''' Called when module needs to shut down, e.g, when we need to reload it '''
        pass

    def apply_config(self, config_section):
        self.config_section = config_section
