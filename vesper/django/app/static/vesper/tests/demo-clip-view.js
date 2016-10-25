'use strict'


class DemoClipView {
	
	
	constructor(parent, clip, settings) {
		this._parent = parent;
		this._clip = clip;
		this._settings = settings;
		this._div = null;
	}
	
	
	get parent() {
		return this._parent;
	}
	
	
	get clip() {
		return this._clip;
	}
	
	
	get settings() {
		return this._settings;
	}
	
	
	set settings(settings) {
		this._settings = settings;
	}
	
	
	get duration() {
		return this.clip.span;
	}
	
	
	get div() {
		
		if (this._div === null)
			this._div = this._createDiv();
		
		return this._div;
		
	}
	
	
	_createDiv() {
		
		const document = this.parent.div.ownerDocument;
		
		const div = document.createElement('div');
		
		const canvas = document.createElement('canvas');
		canvas.className = 'clip-canvas';
		div.appendChild(canvas);
		this._canvas = canvas;
		
	    const label = document.createElement('p');
	    label.className = 'clip-label';
	    label.innerHTML = (this.clip.index + 1).toString();
	    div.appendChild(label);
	    
	    return div;

	}
	
	
	render() {
		
		const div = this.div;
		
		const canvas = this._canvas;
		const width = canvas.clientWidth;
		const height = canvas.clientHeight;
		
		canvas.width = width;
		canvas.height = height;
		
		const size = 20;
		const left = (width - size) / 2;
		const top = (height - size) / 2;
		const right = (width + size) / 2;
		const bottom = (height + size) / 2;

		const context = canvas.getContext('2d');
		context.beginPath();
		context.moveTo(left, top);
		context.lineTo(right, bottom);
		context.moveTo(right, top);
		context.lineTo(left, bottom);
		context.lineWidth = 2;
		context.stroke()
		
	}
	
	
}
