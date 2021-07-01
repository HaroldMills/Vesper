export class CommandableOverlay {


    constructor(
            clipView, settings, defaultCommandableName, commandableDelegate) {
        
        this.clipView = clipView;
        this.clipAlbum = clipView.clipAlbum;

        this.settings = settings;
        
        this.commandableName =
            this._getCommandableName(settings, defaultCommandableName);
            
        this._commandableDelegate = commandableDelegate;
        
    }


    _getCommandableName(settings, defaultName) {
        if (settings.name === undefined)
            return defaultName;
        else
            return settings.name;
    }


    hasCommand(commandName) {
        return this._commandableDelegate.hasCommand(commandName);
    }


    executeCommand(command, env) {
        this._commandableDelegate.executeCommand(command, this, env);
    }


}
