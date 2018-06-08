import { ClipAlbum } from '/static/vesper/clip-album/clip-album.js';


// Module-level state, set via `init` function.
let state = null;


export function init(state_) {

    // Set module-level state.
    state = state_;

    // Install event handlers.
    window.onload = onLoad;
    window.onresize = onResize;

}


let clipAlbum = null;


function onLoad() {
    clipAlbum = new ClipAlbum(state);
}


function onResize() {
    clipAlbum.onResize();
}
