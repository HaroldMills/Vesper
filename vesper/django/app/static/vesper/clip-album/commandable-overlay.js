export class CommandableOverlay {


    constructor(
            clipView, settings, defaultCommandableName, commandableDelegate) {
        
        this.clipView = clipView;
        this.clipAlbum = clipView.clipAlbum;

        this.settings = settings;
        
        this.commandableName =
            this._getCommandableName(settings, defaultCommandableName);
            
        this._commandableDelegate = commandableDelegate;
        
        this._canvas = clipView.overlayCanvas;

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


    _mouseInside(e) {
        const x = e.clientX;
        const y = e.clientY;
        const r = this._canvas.getBoundingClientRect();
        return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
    }


}
