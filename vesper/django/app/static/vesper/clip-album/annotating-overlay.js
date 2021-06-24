export class AnnotatingOverlay {


    constructor(
            clipView, settings, defaultCommandableName, commandableDelegate) {
        
        this.clipView = clipView;
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


    _annotateClip(clipId, annotations) {
        
        const url = '/annotate-clips/'

        const content = {
            'clip_ids': [clipId],
            'annotations': _createObjectFromMap(annotations)
        }
        
        this._sendAnnotationRequest(url, content)
        .then(r => this._onAnnotationRequestFulfilled(r, annotations))
        .catch(this._onAnnotationRequestRejected);

    }


    _sendAnnotationRequest(url, object) {

        return fetch(url, {
            method: 'POST',
            body: JSON.stringify(object),
            headers: new Headers({
                'Content-Type': 'application/json; charset=utf-8'
            }),
            credentials: 'same-origin'
        });

    }


    _onAnnotationRequestFulfilled(response, annotations) {
        
        if (response.status === 200) {
            // Update clip annotations and re-render.

            const clip = this.clipView.clip;
            const annos = clip.annotations;

            if (annos !== null) {
                // client has received clip annotations from server

                for (const [name, value] of annotations.entries())
                    annos.set(name, value);

            } else {
                // client has not yet received clip annotations from server

                // TODO: Not sure what we should do here. We can't
                // update annotations we haven't yet received. Perhaps
                // we should decline to post annotation changes until
                // we have received the original annotations from the
                // server.

            }

            clip.view.render();

        } else {

            window.alert(
                `Clip annotation request failed with response ` +
                `${response.status} (${response.statusText}).`);

        }

    }


    _onAnnotationRequestRejected(error) {
        window.alert(
            `Clip annotation request failed with message: ${error.message}.`);
    }


}


function _createObjectFromMap(map) {
    
    const object = {};
    
    for (const [key, value] of map.entries())
        object[key] = value;
        
    return object;
    
}
