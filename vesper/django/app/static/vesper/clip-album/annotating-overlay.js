export class AnnotatingOverlay {


    constructor(
            clipView, settings, defaultCommandableName, commandableDelegate) {
        
        this.clipView = clipView;
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
        console.log('AnnotatingOverlay.executeCommand', command);
        this._commandableDelegate.executeCommand(command, this, env);
    }


    _annotateClip(clipId, annotations) {
        
        const url = `/clips/${clipId}/annotations/json/`;

        this._postJson(url, annotations)
        .then(r => this._onAnnotationsPostFulfilled(r, annotations))
        .catch(this._onAnnotationsPostRejected);

    }


    _postJson(url, object) {

        return fetch(url, {
            method: 'POST',
            body: JSON.stringify(object),
            headers: new Headers({
                'Content-Type': 'application/json; charset=utf-8'
            }),
            credentials: 'same-origin'
        });

    }


    _onAnnotationsPostFulfilled(response, annotations) {

        if (response.status === 200) {
            // Update clip annotations and re-render.

            const clip = this.clipView.clip;
            const clip_annos = clip.annotations;

            if (clip_annos !== null) {
                // client has received clip annotations from server

                for (const name of Object.getOwnPropertyNames(annotations)) {

                    const value = annotations[name];

                    if (value === null)
                        delete clip_annos[name]
                    else
                        clip_annos[name] = value;

                }

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


    _onAnnotationsPostRejected(error) {
        window.alert(
            `Clip annotation request failed with exception: ` +
            `${error.message}.`);
    }


}
